from app import db

class RentedProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
