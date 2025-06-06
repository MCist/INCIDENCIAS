# app/services/incident_service.py

import os
import getpass
from uuid import uuid4
from flask import current_app
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import RegIncidencia, EvidenciaIncidencia, db
from app.services.utils import obtener_datos_elemento, allowed_file


def registrar_incidencia(form, files):
    # 1) Validar campos obligatorios
    tipo_elemento = form.get("tipo_elemento")

    if tipo_elemento == 'Vano':
        ini = form.get("codigo_inicio") or ''
        fin = form.get("codigo_fin") or ''
        ini = ini.strip()
        fin = fin.strip()
        codigo_elemento = f"{ini} – {fin}" if (ini and fin) else (ini or fin)

        # Extraigo alicodigo a partir del nodo “ini”
        datos_ini = {}
        if ini:
            datos_ini = obtener_datos_elemento('Estructura MT', ini) or {}
        alicodigo = datos_ini.get("alicodigo")
        # Para Vano no consultaremos datos adicionales (por eso no vuelvo a pisar alicodigo)

    else:
        codigo_elemento = form.get("codigo_elemento")
        datos = obtener_datos_elemento(tipo_elemento, codigo_elemento) or {}
        alicodigo = datos.get("alicodigo")

    ocurrencia          = form.get("ocurrencia")
    responsable_id      = form.get("responsable_id")
    tipo_id             = form.get("tipo_id")
    area_responsable_id = form.get("area_responsable_id")
    coord_x_inicio      = form.get("coord_x_inicio")
    coord_y_inicio      = form.get("coord_y_inicio")
    coord_x_fin         = form.get("coord_x_fin")
    coord_y_fin         = form.get("coord_y_fin")
    fecha_str = form.get("fecha_ocurrencia")  # esperado ISO-8601: “2025-06-05” o “2025-06-05T14:30”
    try:
        fecha_ocurrencia = (datetime.fromisoformat(fecha_str)
                            if fecha_str else None)
    except ValueError:
        return None, "Fecha de ocurrencia inválida."

    # Validación de campos obligatorios
    requeridos = [tipo_elemento, ocurrencia, responsable_id, tipo_id, area_responsable_id, fecha_ocurrencia]
    if tipo_elemento != 'Vano':
        requeridos.append(codigo_elemento)
    if not all(requeridos):
        return None, "Faltan campos obligatorios."

    # 2) Para “no‐Vano”, obtenemos datos adicionales y descripción
    datos = {}
    if tipo_elemento != 'Vano':
        datos = obtener_datos_elemento(tipo_elemento, codigo_elemento) or {}
    descripcion = codigo_elemento if tipo_elemento == 'Vano' else datos.get("descripcion")

    # 3) Crear la incidencia (usando alicodigo ya obtenido arriba)
    nueva = RegIncidencia(
        tipo_elemento        = tipo_elemento,
        codigo_elemento      = codigo_elemento,
        fecha_ocurrencia = fecha_ocurrencia,
        descripcion_elemento = descripcion,
        coord_x_inicio       = float(coord_x_inicio) if coord_x_inicio else None,
        coord_y_inicio       = float(coord_y_inicio) if coord_y_inicio else None,
        coord_x_fin          = float(coord_x_fin)    if coord_x_fin    else None,
        coord_y_fin          = float(coord_y_fin)    if coord_y_fin    else None,
        tipo_id              = int(tipo_id),
        usuario_windows      = getpass.getuser(),
        responsable_id       = int(responsable_id),
        ocurrencia           = ocurrencia,
        area_responsable_id  = int(area_responsable_id),
        alicodigo            = alicodigo
    )
    db.session.add(nueva)
    db.session.flush()  # para que nueva.id exista

    # 4) Procesar evidencias (igual que antes)…
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    for archivo in files.getlist("evidencia"):
        if archivo and archivo.filename and allowed_file(archivo.filename):
            original_name = archivo.filename
            ext = original_name.rsplit(".", 1)[1].lower()
            filename = f"{nueva.id}_{uuid4().hex}.{ext}"
            save_path = os.path.join(upload_folder, filename)
            archivo.save(save_path)
            ev = EvidenciaIncidencia(
                incidencia_id = nueva.id,
                filename      = original_name,
                filepath      = filename
            )
            db.session.add(ev)

    db.session.commit()
    return nueva, None

def update_incidencia(id: int, form, files):
    """Actualiza una incidencia evitando sobrescribir con valores vacíos."""
    incidencia = RegIncidencia.query.get(id)
    if not incidencia:
        return None, "Incidencia no encontrada."

    # ---------- 0. Fecha de ocurrencia ----------
    fecha_str = (form.get("fecha_ocurrencia") or '').strip()
    if fecha_str:
        try:
            incidencia.fecha_ocurrencia = datetime.fromisoformat(fecha_str)
        except ValueError:
            pass  # Si prefieres, devuelve error en lugar de ignorar
    # ---------- 1. Tipo de elemento ----------
    tipo_el_form = (form.get("tipo_elemento") or '').strip()
    tipo_el      = tipo_el_form or incidencia.tipo_elemento
    incidencia.tipo_elemento = tipo_el

    # ---------- 2. Según sea Vano o no ----------
    if tipo_el == 'Vano':
        ini = (form.get("codigo_inicio") or '').strip()
        fin = (form.get("codigo_fin") or '').strip()

        if ini or fin:  # solo actualizo si llega alguno
            nuevo_codigo = f"{ini} – {fin}" if (ini and fin) else (ini or fin)
            incidencia.codigo_elemento      = nuevo_codigo
            incidencia.descripcion_elemento = nuevo_codigo

            # refrescar alicodigo con el nodo ini (si lo hay)
            if ini:
                datos_ini = obtener_datos_elemento('Estructura MT', ini) or {}
                incidencia.alicodigo = datos_ini.get("alicodigo") or incidencia.alicodigo

    else:  # No-Vano
        codigo_form = (form.get("codigo_elemento") or '').strip()
        if codigo_form:                       # evita dejarlo en blanco
            incidencia.codigo_elemento = codigo_form

            datos = obtener_datos_elemento(tipo_el, codigo_form) or {}
            incidencia.descripcion_elemento = (
                datos.get("descripcion") or incidencia.descripcion_elemento
            )

            # intentar refrescar coordenadas
            x0 = (datos.get("pro_x") or datos.get("sub_x") or datos.get("trafo_x") or
                  datos.get("sum_x") or datos.get("poste_x"))
            y0 = (datos.get("pro_y") or datos.get("sub_y") or datos.get("trafo_y") or
                  datos.get("sum_y") or datos.get("poste_y"))
            if x0 is not None and y0 is not None:
                incidencia.coord_x_inicio = float(x0)
                incidencia.coord_y_inicio = float(y0)

            incidencia.alicodigo = datos.get("alicodigo") or incidencia.alicodigo

    # ---------- 3. Ocurrencia ----------
    ocur_form = (form.get("ocurrencia") or '').strip()
    if ocur_form:
        incidencia.ocurrencia = ocur_form

    # ---------- 4. Evidencias nuevas ----------
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    for archivo in files.getlist("evidencia"):
        if archivo and archivo.filename and allowed_file(archivo.filename):
            original = archivo.filename
            ext      = original.rsplit(".", 1)[1].lower()
            fname    = f"{incidencia.id}_{uuid4().hex}.{ext}"
            archivo.save(os.path.join(upload_folder, fname))
            ev = EvidenciaIncidencia(
                incidencia_id = incidencia.id,
                filename      = original,
                filepath      = fname
            )
            db.session.add(ev)

    db.session.commit()
    return incidencia, None