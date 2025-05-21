# setup_db.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# Define a local SQLAlchemy instance for setup_db.py
local_db = SQLAlchemy()

# Create a minimal Flask app for database setup
app = Flask(__name__)

# Configure the app for database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///etp.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the local_db instance with this app
local_db.init_app(app)

# Import models after local_db is initialized to ensure they use this db instance
# This import needs to be here to avoid circular dependency issues if models.py
# imports 'db' from 'app.extensions'.
from app.models import User, Lab, Computer # Import all models needed for creation

with app.app_context():
    # Create all database tables using the local_db instance
    local_db.create_all()
    print("✅ Database tables created.")

    # IMPORTANT: After creating tables, remove the current session and get a new one.
    # This ensures the session is aware of the newly created schema.
    local_db.session.remove() 

    # Create a default admin user if one doesn't exist
    # Use local_db.session for operations
    if not local_db.session.query(User).filter_by(username='admin').first():
        hashed_password = generate_password_hash('admin_password') # **CHANGE THIS IN PRODUCTION**
        admin_user = User(username='admin', password=hashed_password, role='admin', user_type='staff')
        local_db.session.add(admin_user)
        local_db.session.commit()
        print("✅ Default admin user created (username: admin, password: admin_password)")
    else:
        print("ℹ️ Admin user already exists.")

