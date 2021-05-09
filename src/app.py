import configparser
import netifaces
from functools import wraps
import connexion
import urllib3
from flask_migrate import Migrate
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import jwt
from consul import Consul, Check
import time

JWT_SECRET = '3cZDYwjsbHYwR94w'
JWT_LIFETIME_SECONDS = 600000

consul_port = 5001
service_name = "reserve"
service_port = 5000

connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reserve-db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

inventory_ms_base_url = 'http://localhost:5001/api'
payment_ms_base_url = 'http://localhost:5002/api'
location_ms_base_url = 'http://localhost:5003/api/locations'


import models

http = urllib3.PoolManager()

def get_ip():
    interface_name = config_parser['NETWORK']['interface']
    ip = netifaces.ifaddresses(interface_name)[netifaces.AF_INET][0]["addr"]
    return ip

def register_to_consul():
    consul = Consul(host="consul", port=consul_port)

    agent = consul.agent

    service = agent.service

    ip = get_ip()

    check = Check.http(f"http://{ip}:{service_port}/", interval="10s", timeout="5s", deregister="1s")

    service.register(service_name, service_id=service_name, address=ip, port=service_port, check=check)

def get_service(service_id):
    consul = Consul(host="consul", port=consul_port)

    agent = consul.agent

    service_list = agent.services()

    service_info = service_list[service_id]

    return service_info['Address'], service_info['Port']

register_to_consul()

def index():
    return "reserve"

def has_role(arg):
    def has_role_inner(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            try:
                headers = request.headers
                if 'AUTHORIZATION' in headers:
                    token = headers['AUTHORIZATION'].split(' ')[1]
                    decoded_token = decode_token(token)
                    if 'admin' in decoded_token['roles']:
                        return fn(*args, **kwargs)
                    for role in arg:
                        if role in decoded_token['roles']:
                            return fn(*args, **kwargs)
                    abort(401)
                return fn(*args, **kwargs)
            except Exception as e:
                abort(401)
        return decorated_view
    return has_role_inner

@has_role('reserve')
def getAllTransferProducts():
    transferProductsRent = db.session.query(models.TransferProductRent).all()
    transferProductsPark = db.session.query(models.TransferProductPark).all()
    return { transferProductsRent, transferProductsPark }, 200

@has_role('reserve')
def rentTransferProduct(product_id):
    res = http.request('POST',"{inventory_ms_base_url}/get/all_products_rent")
    products = json.loads(res.data.decode('utf-8'))
    exists = False
    for product in products:
        exists = product.id==product_id
    if exists == False:
        return {'message':'Product doesn\'t exist!'},404
    http.request('GET',"{inventory_ms_base_url}/rent_product/{product_id}/{user_id}")
    transferProductRent = models.TransferProductRent(
        parkedByUser = extract_user_id(request.headers),
        dateParked = datetime.now(),
        product_id = product_id
    )
    db.session.add(transferProductRent)
    db.session.commit()
    return { transfer_product_rent_id: transferProductRent.id }

@has_role('reserve')
def payTransferProductRent(transfer_product_rent_id):
    user_id = extract_user_id(request.headers)
    transferProductRent = db.session.query(models.TransferProductRent).filter_by(id=transfer_product_rent_id).first()
    res = http.request('GET',"{inventory_ms_base_url}/get_price_for_product_rent/{product_id}")
    price = res.data.decode('utf-8')
    http.request('POST',"{payment_ms_base_url}/pay/rent_pay",fields={
        amount: price,
        user_id:user_id
    })
    db.session.delete(transferProductRent)
    db.session.commit()
    return {'done':True}

@has_role('reserve')
def parkTransferProduct(product_id,parking_spot_id,parking_zone_id):
    user_id = extract_user_id(request.headers)
    http.request('POST',"http://localhost:5005/api/locations/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}")
    transferProductPark = models.TransferProductPark(
        parkedByUser = extract_user_id(request.headers),
        dateParked = datetime.now(),
        product_id = product_id,
        parking_spot_id = parking_spot_id,
        parking_zone_id = parking_zone_id
    )
    db.session.add(transferProductPark)
    db.session.commit()
    return { transfer_product_park_id: transferProductPark.id }

@has_role('reserve')
def payTransferProductPark(transfer_product_park_id):
    transferProductPark = db.session.query(models.TransferProductPark).filter_by(id=transfer_product_park_id).first()
    http.request('PUT',"{location_ms_base_url}/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}")
    http.request('POST',"{payment_ms_base_url}/pay/parking_pay",fields={
        amount: 5 # PLACEHOLDER
    })
    db.session.delete(transferProductPark)
    db.session.commit()
    return {'done':True}

def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

def extract_user_id(headers):
    headers = request.headers
    token = headers['AUTHORIZATION'].split(' ')[1]
    decoded_token = decode_token(token)
    return decode_token.sub

connexion_app.add_api("api.yaml")

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5000, debug=True)
