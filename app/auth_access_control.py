from functools import wraps
from flask import session, redirect, url_for, flash
from app.models import User, Lab, UserLabAssociation # Ensure all necessary models are imported

def require_roles(roles):
    """
    Decorator to restrict access to routes based on user roles.
    If the user is not logged in, they are redirected to the login page.
    If the user's role is not in the allowed roles, they are redirected to the index page.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("You must be logged in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            
            user = User.query.get(session['user_id'])
            if not user or user.role not in roles:
                flash("Unauthorized access.", "danger")
                return redirect(url_for('main.index')) # Redirect to a generic index or error page
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Specific decorators for clarity and ease of use based on roles
def require_logged_in(f):
    """
    Decorator to ensure a user is logged in to access a route.
    This is a general check for any authenticated user.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to ensure only 'admin' role users can access a route."""
    return require_roles(['admin'])(f)

def require_superuser(f):
    """Decorator to ensure 'admin' or 'superuser' role users can access a route."""
    return require_roles(['admin', 'superuser'])(f)

def require_user_role(f):
    """Decorator to ensure 'admin', 'superuser', or 'user' role users can access a route."""
    return require_roles(['admin', 'superuser', 'user'])(f)

def require_guest_role(f):
    """Decorator to ensure 'admin', 'superuser', 'user', or 'guest' role users can access a route."""
    return require_roles(['admin', 'superuser', 'user', 'guest'])(f)

def restrict_lab_access(f):
    """
    Decorator to ensure a user has permission to access data for a specific lab.
    Admins have universal access. Other roles are restricted to their associated labs.
    Assumes 'lab_name' is passed as a keyword argument in the route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        
        user = User.query.get(session['user_id'])
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for('auth.login'))
            
        # Admins have universal access, bypass lab restriction
        if user.role == 'admin':
            return f(*args, **kwargs) 
        
        # For non-admin roles, check lab association
        if 'lab_name' in kwargs: 
            requested_lab_name = kwargs['lab_name']
            
            # Get the user's associated lab names through the association proxy
            user_lab_names = user.lab_names 

            if requested_lab_name not in user_lab_names:
                flash(f"You do not have permission to access data for lab '{requested_lab_name}'.", "danger")
                # Redirect to their own dashboard or a general unauthorized page
                if user.labs: # If they have at least one lab, redirect to their default lab dashboard
                    return redirect(url_for('lab.view_lab_details', lab_name=user.labs[0].lab.name))
                else: # If no labs associated, redirect to main index
                    return redirect(url_for('main.index'))
        else: 
             # If this decorator is used on a route that doesn't pass 'lab_name'
             # but is intended for lab-specific users, ensure they have *any* lab access.
             if user.role != 'admin' and not user.labs: 
                flash("You are not associated with any lab.", "danger")
                return redirect(url_for('main.index'))

        return f(*args, **kwargs)
    return decorated_function
