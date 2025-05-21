from app.auth_access_control import require_logged_in, restrict_lab_access, require_roles # Removed require_lab_user, added require_roles
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from app import db
from app.models import Lab, Computer, User, UserLabAssociation
import csv, os
from werkzeug.utils import secure_filename
import io # For export_csv_for_lab

lab = Blueprint('lab', __name__, url_prefix='/lab')

@lab.route('/')
@require_logged_in
def lab_dashboard():
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        # Admins will see a list of all labs they can manage
        labs = Lab.query.all()
        return render_template('lab/admin_lab_selector.html', labs=labs)
    elif user.labs:
        # For non-admin users, redirect to their first associated lab, or show a selector if multiple
        if len(user.labs) == 1:
            return redirect(url_for('lab.view_lab_details', lab_name=user.labs[0].lab.name))
        else:
            return render_template('lab/user_lab_selector.html', user_labs=user.labs)
    else:
        flash("You are not associated with any lab.", "danger")
        return redirect(url_for('main.index'))

@lab.route('/<lab_name>')
@require_roles(['admin', 'superuser', 'user']) # Used require_roles directly
@restrict_lab_access # Ensures user has access to this specific lab
def view_lab_details(lab_name):
    lab = Lab.query.filter_by(name=lab_name).first_or_404()
    # Computers related to this lab
    computers = Computer.query.filter_by(lab_id=lab.id).all()
    return render_template('lab/lab_dashboard.html', lab=lab, computers=computers)

@lab.route('/edit/<int:computer_id>', methods=['GET', 'POST'])
@require_roles(['admin', 'superuser', 'user']) # Used require_roles directly
# Note: restrict_lab_access should ideally be applied to routes handling lab_name in URL.
# For edit_computer, we need to check permissions based on the fetched computer's lab_id.
def edit_computer(computer_id):
    comp = Computer.query.get_or_404(computer_id)
    # Additional check: ensure the current user is authorized for this specific lab
    user = User.query.get(session['user_id'])
    if user.role != 'admin' and comp.lab.name not in user.lab_names:
        flash("You do not have permission to edit this computer.", "danger")
        return redirect(url_for('lab.lab_dashboard')) # Redirect to their own lab dashboard or general page

    if request.method == 'POST':
        comp.owner = request.form.get('owner', comp.owner)
        comp.justification = request.form.get('justification', comp.justification)
        comp.status = request.form.get('status', comp.status) # Allow updating status
        db.session.commit()
        flash("Computer updated.", "success")
        return redirect(url_for('lab.view_lab_details', lab_name=comp.lab.name))
    return render_template('lab/edit_computer.html', computer=comp)

@lab.route('/import/<lab_name>', methods=['GET', 'POST'])
@require_roles(['admin', 'superuser', 'user']) # Used require_roles directly
@restrict_lab_access
def import_csv_for_lab(lab_name):
    lab = Lab.query.filter_by(name=lab_name).first_or_404()
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file:
            flash("No file selected", 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join('/tmp', filename)
        file.save(filepath)

        imported_data = []
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            reader.fieldnames = [field.strip() for field in reader.fieldnames]
            for row in reader:
                # Assuming CSV has 'ComputerName', 'Owner', 'BusinessJustification', 'Status'
                identifier = ""
                if row.get("ComputerName", "").strip():
                    identifier = f"CN:{row['ComputerName'].strip()}"
                elif row.get("SerialNumber", "").strip():
                    identifier = f"SN:{row['SerialNumber'].strip()}"
                elif row.get("MAC", "").strip():
                    identifier = f"MAC:{row['MAC'].strip()}"
                elif row.get("Hostname", "").strip():
                    identifier = f"HN:{row['Hostname'].strip()}"
                elif row.get("Barcode", "").strip():
                    identifier = f"BC:{row['Barcode'].strip()}"
                elif row.get("Model", "").strip():
                    identifier = f"MD:{row['Model'].strip()}"
                elif row.get("Notes", "").strip():
                    identifier = f"NT:{row['Notes'].strip()}"
                
                if not identifier:
                    identifier = "UNKNOWN"
                    
                owner_val = ""
                if row.get("Owner", "").strip():
                    owner_val = f"OWN:{row['Owner'].strip()}"
                elif row.get("UserName", "").strip():
                    owner_val = f"USR:{row['UserName'].strip()}"
                elif row.get("Lab", "").strip():
                    owner_val = f"LAB:{row['Lab'].strip()}"
                elif row.get("Location", "").strip():
                    owner_val = f"LOC:{row['Location'].strip()}"

                if not owner_val:
                    owner_val = "UNKNOWN"
                    
                status = row.get("Status", "pending").strip().lower()

                imported_data.append({
                    'identifier': identifier,
                    'owner': owner_val,
                    'justification': row.get('BusinessJustification', '').strip(),
                    'status': status
                })
        
        # Simple overwrite/merge for now, consider adding conflict resolution if needed for lab users
        for device in imported_data:
            existing = None
            if device['identifier'].startswith("CN:"):
                existing = Computer.query.filter_by(lab_id=lab.id, computer_name=device['identifier'][3:]).first()
            elif device['identifier'].startswith("SN:"):
                existing = Computer.query.filter_by(lab_id=lab.id, serial_number=device['identifier'][3:]).first()
            elif device['identifier'].startswith("MAC:"):
                existing = Computer.query.filter_by(lab_id=lab.id, mac_address=device['identifier'][4:]).first()
            elif device['identifier'].startswith("HN:"):
                existing = Computer.query.filter_by(lab_id=lab.id, computer_name=device['identifier'][3:]).first()
            elif device['identifier'].startswith("BC:"):
                existing = Computer.query.filter_by(lab_id=lab.id, serial_number=device['identifier'][3:]).first()
            elif device['identifier'].startswith("MD:"):
                existing = Computer.query.filter_by(lab_id=lab.id, computer_name=device['identifier'][3:]).first()

            if existing:
                existing.owner = device['owner']
                existing.justification = device['justification']
                existing.status = device['status']
            else:
                kwargs = {
                    'owner': device['owner'],
                    'justification': device['justification'],
                    'lab': lab,
                    'status': device['status']
                }
                if device['identifier'].startswith("CN:"):
                    kwargs['computer_name'] = device['identifier'][3:]
                elif device['identifier'].startswith("SN:"):
                    kwargs['serial_number'] = device['identifier'][3:]
                elif device['identifier'].startswith("MAC:"):
                    kwargs['mac_address'] = device['identifier'][4:]
                elif device['identifier'].startswith("HN:"):
                    kwargs['computer_name'] = device['identifier'][3:]
                elif device['identifier'].startswith("BC:"):
                    kwargs['serial_number'] = device['identifier'][3:]
                elif device['identifier'].startswith("MD:"):
                    kwargs['computer_name'] = device['identifier'][3:]
                elif device['identifier'].startswith("NT:"):
                    kwargs['justification'] = device['identifier'][3:]
                db.session.add(Computer(**kwargs))
        
        db.session.commit()
        os.remove(filepath)
        flash("Import completed successfully!", "success")
        return redirect(url_for('lab.view_lab_details', lab_name=lab.name))

    return render_template('lab/import_csv_lab.html', lab=lab)

@lab.route('/export/<lab_name>')
@require_roles(['admin', 'superuser', 'user']) # Used require_roles directly
@restrict_lab_access
def export_csv_for_lab(lab_name):
    lab = Lab.query.filter_by(name=lab_name).first_or_404()
    computers = Computer.query.filter_by(lab_id=lab.id).all()

    # Create a CSV in memory
    si = io.StringIO()
    fieldnames = ['Lab', 'ComputerName', 'SerialNumber', 'MAC', 'Owner', 'BusinessJustification', 'Status']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()

    for comp in computers:
        row = {
            'Lab': lab.name,
            'ComputerName': comp.computer_name if comp.computer_name and not comp.computer_name.startswith(('HN:', 'MD:')) else '',
            'SerialNumber': comp.serial_number if comp.serial_number and not comp.serial_number.startswith('BC:') else '',
            'MAC': comp.mac_address if comp.mac_address else '',
            'Owner': comp.owner if comp.owner and not comp.owner.startswith(('USR:', 'LAB:', 'LOC:')) else '',
            'BusinessJustification': comp.justification if comp.justification else '',
            'Status': comp.status
        }
        # Refine identifier export based on your legend preferences
        if comp.computer_name and comp.computer_name.startswith('HN:'):
            row['ComputerName'] = comp.computer_name[3:]
        if comp.computer_name and comp.computer_name.startswith('MD:'):
            row['ComputerName'] = comp.computer_name[3:]
        if comp.serial_number and comp.serial_number.startswith('BC:'):
            row['SerialNumber'] = comp.serial_number[3:]
        if comp.owner and comp.owner.startswith('USR:'):
            row['Owner'] = comp.owner[4:]
        if comp.owner and comp.owner.startswith('LAB:'):
            row['Owner'] = comp.owner[4:]
        if comp.owner and comp.owner.startswith('LOC:'):
            row['Owner'] = comp.owner[4:]

        writer.writerow(row)

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=lab_{lab_name}_computers.csv"
    output.headers["Content-type"] = "text/csv"
    return output
