from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from app.auth_access_control import require_admin
from app import db
from app.models import Lab, Computer, User, UserLabAssociation
import csv, os, json
from collections import defaultdict
from werkzeug.security import generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length

# --- Robust import for CheckboxSelectMultiple ---
# This attempts to import CheckboxSelectMultiple from common paths.
# If all fail, it defines a basic fallback class to prevent ImportError.
try:
    from wtforms.widgets import CheckboxSelectMultiple
except ImportError:
    try:
        from wtforms.widgets.core import CheckboxSelectMultiple
    except ImportError:
        try:
            from wtforms.widgets.html5 import CheckboxSelectMultiple
        except ImportError:
            # Fallback: Define a dummy class if CheckboxSelectMultiple cannot be imported
            # This allows the application to run, but the widget might not render correctly
            # for the associated fields. A proper WTForms installation is still recommended.
            class CheckboxSelectMultiple:
                def __call__(self, field, **kwargs):
                    return '<div class="alert alert-danger">ERROR: CheckboxSelectMultiple widget missing! Please check WTForms installation.</div>'
            print("WARNING: Could not import CheckboxSelectMultiple from wtforms.widgets, wtforms.widgets.core, or wtforms.widgets.html5.")
            print("Please ensure WTForms is correctly installed (WTForms==3.0.0 recommended) and its structure is standard.")


import io
from flask import make_response

admin = Blueprint('admin', __name__, url_prefix='/admin')

BACKUP_DIR = '/tmp/backups'
os.makedirs(BACKUP_DIR, exist_ok=True)

# Define simple forms for user management (You might want more sophisticated forms with Flask-WTF)
class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('superuser', 'Superuser'), ('user', 'User'), ('guest', 'Guest')], validators=[DataRequired()])
    user_type = SelectField('User Type', choices=[('faculty', 'Faculty'), ('staff', 'Staff'), ('grad_student', 'Graduate Student'), ('undergrad_student', 'Undergraduate Student'), ('guest', 'Guest')], validators=[DataRequired()])
    labs = SelectMultipleField('Associated Labs', coerce=int, validators=[], widget=CheckboxSelectMultiple())

class UserEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField('New Password', validators=[Length(min=6)], description='Leave blank to keep current password')
    role = SelectField('Role', choices=[('admin', 'Admin'), ('superuser', 'Superuser'), ('user', 'User'), ('guest', 'Guest')], validators=[DataRequired()])
    user_type = SelectField('User Type', choices=[('faculty', 'Faculty'), ('staff', 'Staff'), ('grad_student', 'Graduate Student'), ('undergrad_student', 'Undergraduate Student'), ('guest', 'Guest')], validators=[DataRequired()])
    labs = SelectMultipleField('Associated Labs', coerce=int, validators=[], widget=CheckboxSelectMultiple())


# --- Helper Functions for Data Processing ---

def _parse_computer_identifier(row):
    """
    Parses the row to extract a standardized computer identifier.
    Returns a tuple: (identifier_type, identifier_value) or (None, None) if not found.
    """
    if row.get("ComputerName", "").strip():
        return "computer_name", row['ComputerName'].strip()
    elif row.get("SerialNumber", "").strip():
        return "serial_number", row['SerialNumber'].strip()
    elif row.get("MAC", "").strip():
        return "mac_address", row['MAC'].strip()
    elif row.get("Hostname", "").strip():
        return "computer_name", f"HN:{row['Hostname'].strip()}"
    elif row.get("Barcode", "").strip():
        return "serial_number", f"BC:{row['Barcode'].strip()}"
    elif row.get("Model", "").strip():
        return "computer_name", f"MD:{row['Model'].strip()}"
    elif row.get("Notes", "").strip():
        return "justification", f"NT:{row['Notes'].strip()}" # Notes can be an identifier for justification
    return None, None

def _parse_owner_field(row):
    """
    Parses the row to extract a standardized owner string.
    Returns the owner string or "UNKNOWN".
    """
    if row.get("Owner", "").strip():
        return f"OWN:{row['Owner'].strip()}"
    elif row.get("UserName", "").strip():
        return f"USR:{row['UserName'].strip()}"
    elif row.get("Lab", "").strip():
        # Note: 'Lab' column is primarily for lab_name, but can be used for owner if specified
        return f"LAB:{row['Lab'].strip()}"
    elif row.get("Location", "").strip():
        return f"LOC:{row['Location'].strip()}"
    return "UNKNOWN"

def _find_computer_by_identifier(lab_id, identifier_type, identifier_value):
    """
    Finds a computer in a specific lab by its identifier type and value.
    Handles prefixed identifiers by stripping the prefix for the lookup.
    """
    if identifier_type == "computer_name":
        if identifier_value.startswith("CN:"):
            return Computer.query.filter_by(lab_id=lab_id, computer_name=identifier_value[3:]).first()
        elif identifier_value.startswith("HN:"):
            return Computer.query.filter_by(lab_id=lab_id, computer_name=identifier_value[3:]).first()
        elif identifier_value.startswith("MD:"):
            return Computer.query.filter_by(lab_id=lab_id, computer_name=identifier_value[3:]).first()
        else: # Assume it's a raw computer name
            return Computer.query.filter_by(lab_id=lab_id, computer_name=identifier_value).first()
    elif identifier_type == "serial_number":
        if identifier_value.startswith("SN:"):
            return Computer.query.filter_by(lab_id=lab_id, serial_number=identifier_value[3:]).first()
        elif identifier_value.startswith("BC:"):
            return Computer.query.filter_by(lab_id=lab_id, serial_number=identifier_value[3:]).first()
        else: # Assume it's a raw serial number
            return Computer.query.filter_by(lab_id=lab_id, serial_number=identifier_value).first()
    elif identifier_type == "mac_address":
        if identifier_value.startswith("MAC:"):
            return Computer.query.filter_by(lab_id=lab_id, mac_address=identifier_value[4:]).first()
        else: # Assume it's a raw MAC address
            return Computer.query.filter_by(lab_id=lab_id, mac_address=identifier_value).first()
    elif identifier_type == "justification" and identifier_value.startswith("NT:"):
        # This case is tricky as justification is not a unique identifier for lookup
        # It's better to rely on actual unique identifiers (CN, SN, MAC) for finding existing records.
        # For 'NT:' it means the computer name/serial/mac was empty, so it's likely a new entry.
        return None 
    return None


def _create_or_update_computer(lab, device_data, mode, conflicts):
    """
    Creates a new Computer record or updates an existing one based on import mode.
    Handles identifier and owner prefixes.
    """
    identifier_type, identifier_value = device_data['identifier_type'], device_data['identifier_value']
    owner_val = device_data['owner']
    justification_val = device_data['justification']
    status_val = device_data['status']

    existing_comp = _find_computer_by_identifier(lab.id, identifier_type, identifier_value)

    if existing_comp:
        if mode == 'retain':
            return # Skip existing records
        elif mode == 'merge':
            changed = False
            if owner_val and owner_val != existing_comp.owner:
                existing_comp.owner = owner_val
                changed = True
            if justification_val and justification_val != existing_comp.justification:
                existing_comp.justification = justification_val
                changed = True
            if status_val and status_val != existing_comp.status:
                existing_comp.status = status_val
                changed = True

            if changed:
                conflicts.append({
                    'lab': lab.name,
                    'identifier': f"{identifier_type.upper()[:2]}:{identifier_value}", # Reconstruct for display
                    'new': device_data,
                    'existing': {
                        'owner': existing_comp.owner,
                        'justification': existing_comp.justification,
                        'status': existing_comp.status
                    }
                })
        elif mode == 'overwrite':
            existing_comp.owner = owner_val
            existing_comp.justification = justification_val
            existing_comp.status = status_val
    else:
        kwargs = {
            'owner': owner_val,
            'justification': justification_val,
            'lab': lab,
            'status': status_val
        }
        if identifier_type == "computer_name":
            kwargs['computer_name'] = identifier_value
        elif identifier_type == "serial_number":
            kwargs['serial_number'] = identifier_value
        elif identifier_type == "mac_address":
            kwargs['mac_address'] = identifier_value
        elif identifier_type == "justification": # For 'NT:' case, store in justification
            kwargs['justification'] = identifier_value.replace("NT:", "") # Remove prefix for storage
            # Since no other identifier, set computer_name to UNKNOWN or similar
            kwargs['computer_name'] = "UNKNOWN" 
        
        db.session.add(Computer(**kwargs))


# --- Routes ---

@admin.route('/labs')
@require_admin
def admin_dashboard():
    labs = Lab.query.all()
    return render_template('admin_dashboard.html', labs=labs)

@admin.route('/users')
@require_admin
def manage_users():
    users = User.query.all()
    labs = Lab.query.all() # To assign labs to users
    return render_template('admin/manage_users.html', users=users, labs=labs)

@admin.route('/users/add', methods=['GET', 'POST'])
@require_admin
def add_user():
    form = UserForm()
    labs = Lab.query.all()
    form.labs.choices = [(lab.id, lab.name) for lab in labs]
    
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password, 
                        role=form.role.data, user_type=form.user_type.data)
        db.session.add(new_user)
        db.session.commit() # Commit to get new_user.id
        
        # Associate labs
        for lab_id in form.labs.data:
            user_lab_assoc = UserLabAssociation(user_id=new_user.id, lab_id=lab_id)
            db.session.add(user_lab_assoc)
        db.session.commit()
        
        flash("User added successfully!", "success")
        return redirect(url_for('admin.manage_users'))
        
    return render_template('admin/add_user.html', form=form)

@admin.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@require_admin
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    
    labs = Lab.query.all()
    form.labs.choices = [(lab.id, lab.name) for lab in labs]
    
    if request.method == 'GET':
        # Pre-populate selected labs for GET request
        form.labs.data = [assoc.lab_id for assoc in user.labs]

    if form.validate_on_submit():
        user.username = form.username.data
        user.role = form.role.data
        user.user_type = form.user_type.data
        if form.password.data: # Only update password if provided
            user.password = generate_password_hash(form.password.data)

        # Update lab associations
        UserLabAssociation.query.filter_by(user_id=user.id).delete() # Remove existing
        for lab_id in form.labs.data:
            user_lab_assoc = UserLabAssociation(user_id=user.id, lab_id=lab_id)
            db.session.add(user_lab_assoc)
        db.session.commit()

        flash("User updated successfully!", "success")
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', form=form, user=user)

@admin.route('/users/delete/<int:user_id>', methods=['POST'])
@require_admin
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for('admin.manage_users'))

@admin.route('/etp-requests')
@require_admin
def etp_requests_dashboard():
    # Fetch all computers, ordered by lab and then status
    all_computers = Computer.query.order_by(Computer.lab_id, Computer.status).all()
    
    # Group computers by lab for display
    labs_with_etps = defaultdict(list)
    for comp in all_computers:
        labs_with_etps[comp.lab].append(comp) # Assuming comp.lab is the Lab object
    
    return render_template('admin/etp_requests_dashboard.html', labs_with_etps=labs_with_etps)


@admin.route('/import', methods=['GET', 'POST'])
@require_admin
def import_csv():
    if request.method == 'POST':
        mode = request.form.get('mode')
        file = request.files.get('csv_file')

        if not file:
            flash("No file selected", 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join('/tmp', filename)
        file.save(filepath)

        conflicts = []
        imported_data = defaultdict(list)

        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            reader.fieldnames = [field.strip() for field in reader.fieldnames]
            for row in reader:
                lab_name = row.get("Lab", "").strip()
                identifier_type, identifier_value = _parse_computer_identifier(row)
                owner_val = _parse_owner_field(row)
                status = row.get("Status", "pending").strip().lower()

                if not identifier_type or not identifier_value:
                    # If no valid identifier, skip this row or handle as an error
                    continue 

                imported_data[lab_name].append({
                    'identifier_type': identifier_type,
                    'identifier_value': identifier_value,
                    'owner': owner_val,
                    'justification': row.get('BusinessJustification', '').strip(),
                    'status': status
                })

        for lab_name, devices in imported_data.items():
            lab = Lab.query.filter_by(name=lab_name).first()
            if not lab:
                lab = Lab(name=lab_name)
                db.session.add(lab)
                db.session.commit()

            # Backup existing data before potential overwrite/revert
            existing_computers = Computer.query.filter_by(lab_id=lab.id).all()
            existing_snapshot = []
            for comp in existing_computers:
                # Reconstruct identifier for snapshot based on which field is populated
                if comp.computer_name:
                    id_str = f"CN:{comp.computer_name}"
                elif comp.serial_number:
                    id_str = f"SN:{comp.serial_number}"
                elif comp.mac_address:
                    id_str = f"MAC:{comp.mac_address}"
                else:
                    id_str = "UNKNOWN" # Fallback if no identifier was stored
                
                existing_snapshot.append({
                    'identifier': id_str,
                    'owner': comp.owner,
                    'justification': comp.justification,
                    'status': comp.status
                })

            if mode != 'revert':
                with open(os.path.join(BACKUP_DIR, f"{lab.name}.json"), 'w') as bf:
                    json.dump(existing_snapshot, bf)

            if mode == 'revert':
                backup_file = os.path.join(BACKUP_DIR, f"{lab.name}.json")
                if os.path.exists(backup_file):
                    with open(backup_file, 'r') as bf:
                        restored = json.load(bf)
                    Computer.query.filter_by(lab_id=lab.id).delete()
                    for item in restored:
                        kwargs = {
                            'owner': item['owner'],
                            'justification': item['justification'],
                            'lab': lab,
                            'status': item['status']
                        }
                        # Parse identifier from backup snapshot for restoration
                        if item['identifier'].startswith("CN:"):
                            kwargs['computer_name'] = item['identifier'][3:]
                        elif item['identifier'].startswith("SN:"):
                            kwargs['serial_number'] = item['identifier'][3:]
                        elif item['identifier'].startswith("MAC:"):
                            kwargs['mac_address'] = item['identifier'][4:]
                        elif item['identifier'].startswith("HN:"):
                            kwargs['computer_name'] = item['identifier'][3:]
                        elif item['identifier'].startswith("BC:"):
                            kwargs['serial_number'] = item['identifier'][3:]
                        elif item['identifier'].startswith("MD:"):
                            kwargs['computer_name'] = item['identifier'][3:]
                        elif item['identifier'].startswith("NT:"):
                            kwargs['justification'] = item['identifier'][3:]
                        elif item['identifier'] == "UNKNOWN":
                            # Handle UNKNOWN case for restoration, maybe leave identifier fields None
                            pass 
                        
                        db.session.add(Computer(**kwargs))
                    db.session.commit() # Commit after restoring all items for a lab
                    continue # Move to next lab in imported_data

            if mode == 'overwrite':
                Computer.query.filter_by(lab_id=lab.id).delete()
                db.session.commit() # Commit the deletion before adding new items

            for device in devices:
                _create_or_update_computer(lab, device, mode, conflicts)

        db.session.commit() # Final commit for all changes (insert/update)
        os.remove(filepath)

        if conflicts:
            session['conflicts'] = conflicts
            return redirect(url_for('admin.resolve_conflicts'))

        flash("Import completed successfully", 'success')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('admin/import_csv.html')

@admin.route('/resolve-conflicts', methods=['GET', 'POST'])
@require_admin
def resolve_conflicts():
    conflicts = session.get('conflicts', [])
    if request.method == 'POST':
        for c in conflicts:
            action = request.form.get(f"resolve_{c['lab']}_{c['identifier']}")
            
            # Re-parse identifier from the conflict data to find the computer
            # The 'identifier' in conflicts is already in the format 'PREFIX:VALUE'
            identifier_prefix = c['identifier'].split(':')[0]
            identifier_value = c['identifier'].split(':', 1)[1] if ':' in c['identifier'] else c['identifier']

            lab = Lab.query.filter_by(name=c['lab']).first()
            if not lab:
                continue # Should not happen if data integrity is good

            comp = _find_computer_by_identifier(lab.id, identifier_prefix.lower(), identifier_value)

            if not comp:
                continue # Computer not found, perhaps deleted manually or identifier changed

            if action == 'use_new':
                comp.owner = c['new']['owner']
                comp.justification = c['new']['justification']
                comp.status = c['new']['status']
        db.session.commit()
        session.pop('conflicts', None)
        flash("Conflicts resolved.", 'success')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('admin/conflicts.html', conflicts=conflicts)
