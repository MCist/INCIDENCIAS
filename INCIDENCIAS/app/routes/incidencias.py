# app/routes/incidencias.py
from flask import Blueprint, render_template
import getpass

incidencias_bp = Blueprint(
    "incidencias", __name__, url_prefix="/incidencias"
)

@incidencias_bp.route("/")
def incidencias():
    """Página con la tabla; los datos llegan por AJAX desde el API."""
    return render_template(
        "incidencias.html",
        os_user=getpass.getuser()
    )
