# app/routes/dashboard.py
from flask import Blueprint, render_template
from app.models import AreaResponsable

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('', methods=['GET'])
def dashboard():
    areas = AreaResponsable.query.order_by(AreaResponsable.nombre_area).all()
    return render_template('dashboard.html',
                           areas_responsables=areas)
