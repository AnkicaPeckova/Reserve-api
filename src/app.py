import connexion
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

def healthz():
    return { 'healthy': True }


connexion_app = connexion.App(__name__, specification_dir="./")
app = connexion_app.app
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/reserve-db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
connexion_app.add_api("api.yaml")

if __name__ == "__main__":
    connexion_app.run(host='0.0.0.0', port=5000, debug=True)
