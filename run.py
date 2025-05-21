from app import create_app
from app.extensions import db
from app.models import Lab, Computer

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8000)