# app/routes/mapa.py

from flask import Blueprint, render_template, url_for
from app.models import db, RegIncidencia, TipoIncidencia, Usuario, AreaResponsable, EvidenciaIncidencia, EvidenciaCierre
from app.database.sqlserver import get_sqlserver_connection
from app.services.vano_service import obtener_trazo_vanos
import getpass

mapa_bp = Blueprint('mapa', __name__)

@mapa_bp.route('/mapa')
def mapa():
    # 1. Consultamos todos los datos desde PostgreSQL, incluyendo coord_x_fin / coord_y_fin
    datos = (
        db.session.query(
            RegIncidencia.id,
            RegIncidencia.tipo_elemento,
            RegIncidencia.codigo_elemento,
            RegIncidencia.coord_x_inicio,
            RegIncidencia.coord_y_inicio,
            RegIncidencia.coord_x_fin,
            RegIncidencia.coord_y_fin,
            RegIncidencia.descripcion_elemento,
            RegIncidencia.tipo_id,
            RegIncidencia.responsable_id,
            TipoIncidencia.tipoincidencia,
            TipoIncidencia.peso_tipo,
            Usuario.nombre.label('responsable_nombre'),
            AreaResponsable.nombre_area.label('area_nombre'),
            RegIncidencia.alicodigo,
            RegIncidencia.fecha_reporte,
            RegIncidencia.estado,
            RegIncidencia.ocurrencia
        )
        .join(TipoIncidencia, RegIncidencia.tipo_id == TipoIncidencia.id)
        .join(Usuario, RegIncidencia.responsable_id == Usuario.id)
        .join(AreaResponsable, RegIncidencia.area_responsable_id == AreaResponsable.id)
        # Queremos asegurarnos al menos de que existan coord_inicio para dibujar
        .filter(
            RegIncidencia.coord_x_inicio.isnot(None),
            RegIncidencia.coord_y_inicio.isnot(None)
        )
        .all()
    )

    # 2. Obtenemos todos los alicodigos únicos (para consultar nombre de alimentador)
    alicodigos = {int(d[14]) for d in datos if d[14]}

    # 3. Consultamos los nombres de alimentadores desde SQL Server
    ali_nombre_dict = {}
    if alicodigos:
        try:
            conn = get_sqlserver_connection()
            cursor = conn.cursor()
            # Construimos un string "1,2,3,..." para el IN
            placeholders = ','.join(str(a) for a in alicodigos)
            cursor.execute(f"""
                SELECT AliCodigo, OpCodigo 
                  FROM RDP_Alimentador 
                 WHERE AliCodigo IN ({placeholders})
            """)
            for ali, nombre in cursor.fetchall():
                ali_nombre_dict[int(ali)] = nombre
        except Exception as e:
            print("⚠️ Error consultando nombres de alimentadores:", e)

    # 4. Armamos los datos a enviar al mapa
    coordenadas = []
    for (
        inc_id, tipo_elemento, codigo_elemento, x_ini, y_ini, x_fin, y_fin, descripcion, tipo_id, responsable_id, tipo_nombre,
        peso, responsable_nombre, area_nombre, alicodigo, fecha, estado, ocurrencia
    ) in datos:

        ali_nombre = ali_nombre_dict.get(int(alicodigo), "Desconocido") if alicodigo else "Desconocido"

        # URLs de evidencias
        ev_rep = EvidenciaIncidencia.query.filter_by(incidencia_id=inc_id).all()
        rep_urls = [
            url_for('static', filename='uploads/reporte/' + e.filepath)
            for e in ev_rep
        ]
        ev_cie = EvidenciaCierre.query.filter_by(incidencia_id=inc_id).all()
        cie_urls = [
            url_for('static', filename='uploads/cierre/' + e.filepath)
            for e in ev_cie
        ]

        # ● Si no es “Vano”, enviamos un solo marcador (coordenada de inicio).
        if tipo_elemento != 'Vano':
            coordenadas.append({
                'id'            : inc_id,
                'tipo_elemento' : tipo_elemento,
                'cod'           : codigo_elemento,
                'descripcion'   : descripcion,
                'x_inicio'      : x_ini,
                'y_inicio'      : y_ini,
                'x_fin'         : None,
                'y_fin'         : None,
                'tipo'          : tipo_nombre,
                'peso'          : peso,
                'responsable'   : responsable_nombre,
                'area'          : area_nombre,
                'alicodigo'     : alicodigo,
                'ali_nombre'    : ali_nombre,
                'fecha'         : fecha.isoformat(),
                'estado'        : estado,
                'ocurrencia'    : ocurrencia,
                'ev_rep'        : rep_urls,
                'ev_cie'        : cie_urls,
                # Para marcadores normales, no necesitamos “trazo”
                'trazo'         : None
            })

        else:
            # ● Si es “Vano”, llamamos a nuestro helper para obtener la polilínea
            #   (lista de puntos [lat, lng] que recorre todos los vanos intermedios).
            camino, polilinea = obtener_trazo_vanos(
                codigo_inicio=codigo_elemento.split('–')[0].strip(),
                codigo_fin   =codigo_elemento.split('–')[-1].strip()
            )

            coordenadas.append({
                'id'            : inc_id,
                'tipo_elemento' : tipo_elemento,
                'cod'           : codigo_elemento.strip(),
                'descripcion'   : descripcion,
                'x_inicio'      : x_ini,
                'y_inicio'      : y_ini,
                'x_fin'         : x_fin,
                'y_fin'         : y_fin,
                'tipo'          : tipo_nombre,
                'peso'          : peso,
                'responsable'   : responsable_nombre,
                'area'          : area_nombre,
                'alicodigo'     : alicodigo,
                'ali_nombre'    : ali_nombre,
                'fecha'         : fecha.isoformat(),
                'estado'        : estado,
                'ocurrencia'    : ocurrencia,
                'ev_rep'        : rep_urls,
                'ev_cie'        : cie_urls,
                'trazo'         : polilinea  # <— array de [lat, lng] para cada segmento
            })

    return render_template(
        'map.html',
        coordenadas=coordenadas,
        os_user=getpass.getuser()
    )