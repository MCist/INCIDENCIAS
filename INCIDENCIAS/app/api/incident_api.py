# app/services/incident_api.py
from flask import Blueprint, request, jsonify, current_app
from app.services.utils import obtener_datos_elemento
from app.database.sqlserver import get_sqlserver_connection
from app.models import Usuario, AreaResponsable, TipoIncidencia
from app.services.vano_service import obtener_trazo_vanos

incident_api = Blueprint('incident_api', __name__)

# 1. Datos del elemento según tipo y código
@incident_api.route('/api/datos_elemento')
def datos_elemento():
    tipo = request.args.get('tipo')
    codigo = request.args.get('codigo')

    # Validación básica
    if not tipo or not codigo:
        return jsonify({'error': 'Parámetros faltantes'}), 400
    codigo = codigo.strip()
    # ----------------------------------------------------------
    # Nuevo caso: "Vano" ⇒ esperamos que `codigo` venga en la forma "INI – FIN"
    # ----------------------------------------------------------
    if tipo == 'Vano':
        # Partimos el string en dos (separador “–”, con espacios alrededor)
        partes = [p.strip() for p in codigo.split('–')]
        if len(partes) != 2:
            return jsonify({'error': 'Formato inválido para Vano. Se esperaba "INI – FIN"'}), 400

        ini_cod, fin_cod = partes

        # 1) Obtenemos datos para el nodo de inicio (Estructura MT)
        datos_ini = obtener_datos_elemento('Estructura MT', ini_cod)
        if not datos_ini:
            return jsonify({'error': f'No se encontraron datos para Estructura MT inicio "{ini_cod}"'}), 404

        # 2) Obtenemos datos para el nodo de fin (Estructura MT)
        datos_fin = obtener_datos_elemento('Estructura MT', fin_cod)
        if not datos_fin:
            return jsonify({'error': f'No se encontraron datos para Estructura MT fin "{fin_cod}"'}), 404

        # 3) Armamos la respuesta combinada:
        #    • descripción sencilla = "INI – FIN"
        #    • ali_nombre, uun_nombre, alicodigo del nodo 'inicio'
        #    • coordenadas: inicio = datos_ini['poste_x','poste_y'], fin = datos_fin['poste_x','poste_y']
        respuesta = {
            'descripcion': codigo,
            # Campos “globales” según el nodo inicial:
            'ali_nombre': datos_ini.get('ali_nombre'),
            'uun_nombre': datos_ini.get('uun_nombre'),
            'alicodigo' : datos_ini.get('alicodigo'),
            # Coordenadas de INICIO:
            'poste_x_ini': datos_ini.get('poste_x'),
            'poste_y_ini': datos_ini.get('poste_y'),
            # Coordenadas de FIN:
            'poste_x_fin': datos_fin.get('poste_x'),
            'poste_y_fin': datos_fin.get('poste_y'),
            # Y, si quisieras, podrías regresar también otros campos específicos de cada nodo,
            # por ejemplo propietario, owner_type, etc. (según tus necesidades).
        }
        return jsonify(respuesta)

    # ----------------------------------------------------------
    #   Casos “normales” (uno solo: Estructura MT, Suministro, Pro/Control, etc.)
    # ----------------------------------------------------------
    datos = obtener_datos_elemento(tipo, codigo)
    if not datos:
        return jsonify({'error': f'No se encontraron datos para tipo "{tipo}" y código "{codigo}"'}), 404

    return jsonify(datos)


# 2. Autocompletar código del elemento
@incident_api.route('/api/autocomplete_codigo')
def autocomplete_codigo():
    tipo = request.args.get('tipo')
    term = request.args.get('term', '')

    if not tipo:
        return jsonify([])

    conn = get_sqlserver_connection()
    cursor = conn.cursor()

    # Proteccion/Control
    if tipo == 'Proteccion/Control':
        if term:
            sql = """
                SELECT TOP 10 PuntoMedicion
                  FROM RDP_ProCon
                 WHERE PuntoMedicion LIKE ? AND IdEstado = 1
              ORDER BY PuntoMedicion
            """
            cursor.execute(sql, (f'{term}%',))
        else:
            cursor.execute("""
                SELECT TOP 10 PuntoMedicion
                  FROM RDP_ProCon
                 WHERE IdEstado = 1
              ORDER BY NEWID()
            """)
        resultados = [row[0] for row in cursor.fetchall()]

    # Subestacion
    elif tipo == 'Subestacion':
        if term:
            sql = """
                SELECT TOP 10 SubSubestacion
                  FROM RDS_Subestacion
                 WHERE SubSubestacion LIKE ? AND IdEstado = 1
              ORDER BY SubSubestacion
            """
            cursor.execute(sql, (f'{term}%',))
        else:
            cursor.execute("""
                SELECT TOP 10 SubSubestacion
                  FROM RDS_Subestacion
                 WHERE IdEstado = 1
              ORDER BY NEWID()
            """)
        resultados = [row[0] for row in cursor.fetchall()]

    # Transformador de potencia
    elif tipo == 'Subestación de potencia':
        if term:
            sql = """
                SELECT TOP 10 CenNombre
                  FROM dbo.RDP_CentroTransformacion
                 WHERE CenNombre LIKE ? AND IdEstado = 1 AND TipoPunto NOT IN ('G')
              ORDER BY CenNombre
            """
            cursor.execute(sql, (f'{term}%',))
        else:
            cursor.execute("""
                SELECT TOP 10 CenNombre
                  FROM dbo.RDP_CentroTransformacion
                 WHERE IdEstado = 1 AND TipoPunto NOT IN ('G')
              ORDER BY NEWID()
            """)
        resultados = [row[0] for row in cursor.fetchall()]

    # Suministro
    elif tipo == 'Suministro':
        if term:
            sql = """
                SELECT TOP 10 SumCodigo
                  FROM dbo.comercial
                 WHERE SumCodigo LIKE ?
              ORDER BY SumCodigo
            """
            cursor.execute(sql, (f'{term}%',))
        else:
            cursor.execute("""
                SELECT TOP 10 SumCodigo
                  FROM dbo.comercial
              ORDER BY NEWID()
            """)
        resultados = [row[0] for row in cursor.fetchall()]

    # Estructura MT
    elif tipo == 'Estructura MT':
        if term:
            sql = """
                SELECT TOP 10 NodNtcse
                  FROM dbo.EST_Poste
                 WHERE NodNtcse LIKE ? AND IdEstado = 1 AND NodBTMT = 'M'
              ORDER BY NodNtcse
            """
            cursor.execute(sql, (f'{term}%',))
        else:
            cursor.execute("""
                SELECT TOP 10 NodNtcse
                  FROM dbo.EST_Poste
                 WHERE IdEstado = 1 AND NodBTMT = 'M'
              ORDER BY NEWID()
            """)
        resultados = [row[0].strip() for row in cursor.fetchall()]

    else:
        # Tipo desconocido (o “Vano” ya quedó manejado más arriba)
        resultados = []

    return jsonify(resultados)


# 3. Obtener área del responsable
@incident_api.route('/api/responsable/<int:responsable_id>')
def datos_responsable(responsable_id):
    r = Usuario.query.get(responsable_id)
    if not r:
        return jsonify({'error': 'Responsable no encontrado'}), 404
    return jsonify({'area_id': r.area.id})


# 4. Obtener responsables de un área
@incident_api.route('/api/responsables_area/<int:area_id>')
def responsables_por_area(area_id):
    responsables = Usuario.query.filter_by(id_area=area_id).all()
    return jsonify({
        'responsables': [
            {'id': u.id, 'nombre': u.nombre, 'area': u.area.nombre_area}
            for u in responsables
        ]
    })


# 5. Obtener tipos de incidencia de un área
@incident_api.route('/api/tipos_area/<int:area_id>')
def tipos_por_area(area_id):
    area = AreaResponsable.query.get(area_id)
    if not area:
        return jsonify({'tipos': []})
    return jsonify({
        'tipos': [
            {'id': t.id, 'nombre': t.tipoincidencia}
            for t in area.tipos_incidencias
        ]
    })


# 6. Ruta combinada (área ↔ responsable ↔ tipos)
@incident_api.route('/api/relaciones')
def relaciones():
    area_id        = request.args.get('area_id')
    responsable_id = request.args.get('responsable_id')

    if area_id:
        area = AreaResponsable.query.get(area_id)
        if not area:
            return jsonify({'error': 'Área no encontrada'}), 404
        responsables = [{'id': u.id, 'nombre': u.nombre} for u in area.usuarios]
        tipos         = [{'id': t.id, 'nombre': t.tipoincidencia} for t in area.tipos_incidencias]
        return jsonify({'responsables': responsables, 'tipos': tipos})

    if responsable_id:
        r = Usuario.query.get(responsable_id)
        if not r:
            return jsonify({'error': 'Responsable no encontrado'}), 404
        area = r.area
        tipos = [{'id': t.id, 'nombre': t.tipoincidencia} for t in area.tipos_incidencias]
        return jsonify({
            'area': {'id': area.id, 'nombre': area.nombre_area},
            'tipos': tipos
        })

    return jsonify({'error': 'Parámetros faltantes'}), 400

@incident_api.route('/api/validar_vano')
def validar_vano():
    ini = request.args.get('ini', '').strip()
    fin = request.args.get('fin', '').strip()
    if not ini or not fin:
        return jsonify({'ok': False, 'error': 'Faltan parámetros'}), 400

    try:
        camino, _ = obtener_trazo_vanos(ini, fin)   # <-- CAMBIO
    except Exception as e:
        current_app.logger.error(f"Error al validar vano {ini}–{fin}: {e}")
        return jsonify({'ok': False, 'error': 'Error interno'}), 500

    return jsonify({'ok': bool(camino)})


@incident_api.route('/api/ruta_vano')
def ruta_vano():
    ini = request.args.get('ini', '').strip()
    fin = request.args.get('fin', '').strip()

    if not ini or not fin:
        return jsonify({'error': 'Faltan parámetros'}), 400

    try:
        camino_vanos, polilinea = obtener_trazo_vanos(ini, fin)
    except Exception as e:
        current_app.logger.error(f"Error al obtener trazo_vano {ini}–{fin}: {e}")
        return jsonify({'error': 'Error interno'}), 500

    if not camino_vanos:
        return jsonify({'ok': False, 'ruta': []})

    # Devolvemos ok=true y la lista de puntos (lat, lon)
    return jsonify({'ok': True, 'ruta': polilinea})