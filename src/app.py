from functools import wraps
import connexion
import urllib3
from flask_migrate import Migrate
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import jwt
import time

from consul_functions import get_host_name_IP, get_consul_service, register_to_consul

RESERVE_APIKEY = 'RESERVE MS SECRET'
JWT_LIFETIME_SECONDS = 600000
TOKEN_CREATION_TIME = time.time() - JWT_LIFETIME_SECONDS - 1
AUTH_HEADER = {}

consul_port = 5001
service_name = "reserve-ms"
service_port = 5000

connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reserve-db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

import models

http = urllib3.PoolManager()

def get_jwt_token_from_user_ms():
    # http://localhost:5010/api/user/auth-microservice

    user_ms_url = get_service_url('user-ms')

    url = "{}/api/user/{}".format(user_ms_url, 'auth-microservice')

    res = http.request("POST",url,fields={
        "apikey": RESERVE_APIKEY
    })

    return json.loads(res.data.decode('utf-8'))

def update_jwt_token():

    global TOKEN_CREATION_TIME
    global AUTH_HEADER

    if time.time() - TOKEN_CREATION_TIME > JWT_LIFETIME_SECONDS:
        print("Updating token")
        jwt_token = get_jwt_token_from_user_ms()
        auth_value = "Bearer {}".format(jwt_token)
        AUTH_HEADER = {"Authorization": auth_value}
        TOKEN_CREATION_TIME = time.time()

def get_service_url(service_name):

    discounts_address, discounts_port = get_consul_service(service_name)

    url = "{}:{}".format(discounts_address, discounts_port)

    if not url.startswith("http"):
        url = "http://{}".format(url)
    
    return url

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
    global AUTH_HEADER
    update_jwt_token()
    inventory_ms_base_url = get_service_url('inventory-ms')
    res = http.request('POST',"{inventory_ms_base_url}/get/all_products_rent",headers=AUTH_HEADER)
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
    global AUTH_HEADER
    update_jwt_token()
    inventory_ms_base_url = get_service_url('inventory-ms')
    payment_ms_base_url = get_service_url('payment-ms')
    user_id = extract_user_id(request.headers)
    transferProductRent = db.session.query(models.TransferProductRent).filter_by(id=transfer_product_rent_id).first()
    res = http.request('GET',"{inventory_ms_base_url}/get_price_for_product_rent/{product_id}",headers=AUTH_HEADER)
    price = res.data.decode('utf-8')
    http.request('POST',"{payment_ms_base_url}/pay/rent_pay",fields={
        amount: price,
        user_id:user_id
    },headers=AUTH_HEADER)
    db.session.delete(transferProductRent)
    db.session.commit()
    return {'done':True}

@has_role('reserve')
def parkTransferProduct(product_id,parking_spot_id,parking_zone_id):
    global AUTH_HEADER
    update_jwt_token()
    location_ms_base_url = get_service_url('location-ms')
    user_id = extract_user_id(request.headers)
    http.request('POST',"{location_ms_base_url}/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}",headers=AUTH_HEADER)
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
    global AUTH_HEADER
    update_jwt_token()
    location_ms_base_url = get_service_url('location-ms')
    payment_ms_base_url = get_service_url('payment-ms')
    transferProductPark = db.session.query(models.TransferProductPark).filter_by(id=transfer_product_park_id).first()
    http.request('PUT',"{location_ms_base_url}/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}",headers=AUTH_HEADER)
    http.request('POST',"{payment_ms_base_url}/pay/parking_pay",fields={
        amount: 5 # PLACEHOLDER
    },headers=AUTH_HEADER)
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

register_to_consul()

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5000, debug=True)
