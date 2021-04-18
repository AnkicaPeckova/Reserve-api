from app import db

class TransferProductRent(db.Model):
    __tablename__ = "transfer_product_rent"
    id = db.Column(db.Integer, primary_key=True)
    locationWhereToRent = db.Column(db.String(16))
    locationToLeave = db.Column(db.String(16))
    boolean = db.Column(db.Boolean)
