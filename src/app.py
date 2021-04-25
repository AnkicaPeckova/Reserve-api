from functools import wraps
import connexion
import urllib3
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import jwt
import time

JWT_SECRET = '3cZDYwjsbHYwR94w'
JWT_LIFETIME_SECONDS = 600000

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
    return transferProductsRent, 200

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
    return { 'done': True }

@has_role('reserve')
def payTransferProductRent():
    res = http.request('GET',"{inventory_ms_base_url}/get_price_for_product_rent/{product_id}")
    price = res.data.decode('utf-8')
    http.request('POST',"{payment_ms_base_url}/pay/rent_pay",fields={
        amount: price
    })
    return {'done':True}

@has_role('reserve')
def parkTransferProduct(product_id,parking_spot_id,parking_zone_id):
    http.request('POST',"http://localhost:5005/api/locations/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}")
    return { 'done': True }

@has_role('reserve')
def payTransferProductPark(product_id,parking_spot_id,parking_zone_id):
    http.request('PUT',"{location_ms_base_url}/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}")
    http.request('POST',"{payment_ms_base_url}/pay/parking_pay",fields={
        amount: 5 # PLACEHOLDER
    })
    return {'done':True}

def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

connexion_app.add_api("api.yaml")

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5000, debug=True)
