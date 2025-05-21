from app.extensions import db
from sqlalchemy.ext.associationproxy import association_proxy

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user') # 'admin', 'superuser', 'user', 'guest'
    user_type = db.Column(db.String(50), nullable=False, default='staff') # 'faculty', 'staff', 'grad_student', 'undergrad_student', 'guest'

    # Many-to-many relationship with Lab through UserLabAssociation
    labs = db.relationship('UserLabAssociation', back_populates='user', cascade='all, delete-orphan')
    lab_names = association_proxy('labs', 'lab_name') # For easier access to lab names

class Lab(db.Model):
    __tablename__ = 'lab'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    computers = db.relationship('Computer', back_populates='lab', cascade='all, delete-orphan')
    
    # Relationship for UserLabAssociation
    user_associations = db.relationship('UserLabAssociation', back_populates='lab', cascade='all, delete-orphan')

class UserLabAssociation(db.Model):
    __tablename__ = 'user_lab_association'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), primary_key=True)
    
    user = db.relationship('User', back_populates='labs')
    lab = db.relationship('Lab', back_populates='user_associations')
    
    # Optional: store lab name directly for easier access if needed
    lab_name = association_proxy('lab', 'name')

class Computer(db.Model):
    __tablename__ = 'computer'

    id = db.Column(db.Integer, primary_key=True)
    computer_name = db.Column(db.String(120))
    serial_number = db.Column(db.String(120))
    mac_address = db.Column(db.String(120))
    owner = db.Column(db.String(120))
    justification = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending') # New field: 'pending', 'submitted', 'needs_info', 'retire', 'complete'
    
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=False)
    lab = db.relationship('Lab', back_populates='computers')