from flask import Blueprint, render_template
from app.models import Lab

main = Blueprint('main', __name__)

@main.route("/")
def index():
    return render_template("index.html")

@main.route("/labs/<lab_name>")
def lab_dashboard(lab_name):
    lab = Lab.query.filter_by(name=lab_name).first_or_404()
    return render_template("lab_dashboard.html", lab=lab)