# app/routes/reportar.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Usuario, TipoIncidencia, AreaResponsable
from app.services.incident_service import registrar_incidencia
from app.services.utils import get_os_user

reportar_bp = Blueprint('reportar', __name__)

@reportar_bp.route('/reportar', methods=['GET', 'POST'])

def reportar():
    if request.method == 'POST':
        incidencia, error = registrar_incidencia(request.form, request.files)
        if error:
            flash(error, "danger")
            return redirect(url_for('reportar.reportar'))
        flash("Incidencia registrada correctamente.", "success")
        return redirect(url_for('reportar.reportar'))

    responsables = Usuario.query.order_by(Usuario.nombre).all()
    tipos = TipoIncidencia.query.order_by(TipoIncidencia.tipoincidencia).all()
    areas = AreaResponsable.query.all()
    return render_template('report.html', responsables=responsables, tipos=tipos, areas=areas, os_user=get_os_user())
