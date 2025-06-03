# app/routes/analysis.py
from flask import Blueprint, render_template

bp = Blueprint('analysis', __name__, url_prefix='/analysis')

@bp.route('/fallas')
def fallas():
    return render_template('not_ready.html')
