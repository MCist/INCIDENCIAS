# app/routes/metrics.py
from flask import Blueprint, render_template

bp = Blueprint('metrics', __name__, url_prefix='/metrics')

@bp.route('/saidi_saifi')
def saidi_saifi():
    # Usamos el not_ready.html que ya tienes
    return render_template('not_ready.html')
