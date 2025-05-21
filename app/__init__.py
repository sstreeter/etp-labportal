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

        from app.extensions import login_manager # Import login_manager
        login_manager.init_app(app) # Initialize Flask-Login
        login_manager.login_view = 'auth.login' # Tell Flask-Login where your login route is

    db.init_app(app)
    migrate.init_app(app, db)
# ADD THESE LINES FOR FLASK-LOGIN AND CORRECT BLUEPRINT REGISTRATION
    from app.extensions import login_manager 
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' # Ensure this points to your login route


    from .admin_routes import admin
    from .lab_routes import lab
    from .main_routes import main
    from .auth_routes import auth

    app.register_blueprint(admin)
    app.register_blueprint(lab)
    app.register_blueprint(main)
    #app.register_blueprint(auth)
    app.register_blueprint(auth, url_prefix='/auth') # IMPORTANT: Add url_prefix here
    return app