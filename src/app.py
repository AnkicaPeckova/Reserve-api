import connexion
import urllib3
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

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

def getAllTransferProducts():
    transferProductsRent = db.session.query(models.TransferProductRent).all()
    return transferProductsRent, 200

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

def payTransferProductRent():
    res = http.request('GET',"{inventory_ms_base_url}/get_price_for_product_rent/{product_id}")
    price = res.data.decode('utf-8')
    http.request('POST',"{payment_ms_base_url}/pay/rent_pay",fields={
        amount: price
    })
    return {'done':True}

def parkTransferProduct(product_id,parking_spot_id,parking_zone_id):
    http.request('POST',"http://localhost:5005/api/locations/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}")
    return { 'done': True }

def payTransferProductPark(product_id,parking_spot_id,parking_zone_id):
    http.request('PUT',"{location_ms_base_url}/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}")
    http.request('POST',"{payment_ms_base_url}/pay/parking_pay",fields={
        amount: 5 # PLACEHOLDER
    })
    return {'done':True}

connexion_app.add_api("api.yaml")

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5000, debug=True)
