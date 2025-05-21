# app/auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from app.models import User # Ensure User model is imported

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    - On GET request, renders the login form.
    - On POST request, authenticates the user.
    - If authentication is successful, sets user_id and user_role in session
      and redirects based on role (admin to admin_dashboard, others to lab_dashboard).
    - If authentication fails, flashes an error message.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Query the user from the database
        user = User.query.filter_by(username=username).first()

        # Check if user exists and password is correct
        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))

        # Set user session variables upon successful login
        session['user_id'] = user.id
        session['user_role'] = user.role
        flash('Logged in successfully!', 'success')

        # Redirect based on the user's role
        if user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        else:
            # For non-admin users, redirect to their lab-specific dashboard
            # The lab.lab_dashboard route will handle further redirection based on lab association
            return redirect(url_for('lab.lab_dashboard'))

    # Render the login form for GET requests
    return render_template('login.html')

# You might want to add a logout route here as well
@auth.route('/logout')
def logout():
    """
    Logs out the current user by clearing the session.
    """
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

