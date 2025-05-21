# app/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Dynamically select config class
    env = os.getenv("APP_ENV", "development").lower()

    if env == "production":
        from config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    db.init_app(app)
    migrate.init_app(app, db)

    from .admin_routes import admin
    from .lab_routes import lab
    from .main_routes import main
    from .auth_routes import auth

    app.register_blueprint(admin)
    app.register_blueprint(lab)
    app.register_blueprint(main)
    app.register_blueprint(auth)

    return app