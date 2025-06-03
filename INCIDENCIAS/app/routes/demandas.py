# app/routes/demandas.py
from flask import Blueprint, render_template

bp = Blueprint('demandas', __name__, url_prefix='/demandas')

@bp.route('/maximas')
def maximas():
    return render_template('not_ready.html')

@bp.route('/perfiles')
def perfiles():
    return render_template('not_ready.html')

@bp.route('/realtime')
def realtime():
    return render_template('not_ready.html')
