import connexion
import urllib3
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@postgres:5432/reserve-db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

import models

http = urllib3.PoolManager()

def healthz():
    return { 'healthy': True }

def getAllTransferProducts():
    transferProductsRent = db.session.query(models.TransferProductRent).all()
    return transferProductsRent, 200

def rentTransferProduct(product_id):
    res = http.request('POST',"http://localhost:5008/api/get/all_products_rent")
    products = json.loads(res.data.decode('utf-8'))
    exists = False
    for product in products:
        exists = product.id==product_id
    if exists == False:
        return {'message':'Product doesn\'t exist!'},404
    http.request('POST',"http://localhost:5008/api/reserve_product_rent",fields={
        product_id,
        user_id: 'f6b03ce5-d299-4fb1-84d0-76c09abee2a2' # PLACEHOLDER
    })
    return { 'done': True }

def payTransferProductRent():
    http.request('POST',"http://localhost:5005/api/pay/rent_pay",fields={
        amount: 5 # PLACEHOLDER
    })
    return {'done':True}

def parkTransferProduct(product_id,parking_spot_id,parking_zone_id):
    http.request('POST',"http://localhost:5005/api/locations/parking_spots/{parking_spot_id}/reserve/{parking_zone_id}")
    return { 'done': True }

def payTransferProductPark(product_id,parking_spot_id,parking_zone_id):
    http.request('POST',"http://localhost:5005/api/locations/parking_spots/{parking_spot_id}/free/{parking_zone_id}")
    http.request('POST',"http://localhost:5005/api/pay/parking_pay",fields={
        amount: 5 # PLACEHOLDER
    })
    return {'done':True}

connexion_app.add_api("api.yaml")

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5000, debug=True)
