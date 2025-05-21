from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

# User loader for Flask-Login
from app.models import User # Import here to avoid circular dependency with db init in app/__init__.py

@login_manager.user_loader
def load_user(user_id):
    """
    Given a user ID, return the User object.
    """
    return User.query.get(int(user_id))