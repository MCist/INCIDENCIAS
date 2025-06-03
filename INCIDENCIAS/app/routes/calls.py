# app/routes/calls.py
from flask import Blueprint, render_template

bp = Blueprint('calls', __name__, url_prefix='/calls')

@bp.route('/interrupciones')
def interrupciones():
    return render_template('not_ready.html')
