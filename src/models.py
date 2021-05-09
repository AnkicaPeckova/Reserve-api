from app import db

class TransferProductRent(db.Model):
    __tablename__ = "transfer_product_rent"
    id = db.Column(db.Integer, primary_key=True)
    rentedByUser = db.Column(db.String(36))
    dateRented = db.Column(db.DateTime)
    product_id = db.Column(db.Integer)

class TransferProductPark(db.Model):
    __tablename__ = "transfer_product_park"
    id = db.Column(db.Integer, primary_key=True)
    parkedByUser = db.Column(db.String(36))
    dateParked = db.Column(db.DateTime)
    product_id = db.Column(db.Integer)
    parking_spot_id = db.Column(db.Integer)
    parking_zone_id = db.Column(db.Integer)
