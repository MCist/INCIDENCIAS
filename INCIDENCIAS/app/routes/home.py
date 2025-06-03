# app/routes/home.py
from flask import Blueprint, render_template
import getpass

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def home():
    return render_template('home.html', os_user=getpass.getuser())
