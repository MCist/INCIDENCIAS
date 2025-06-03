# app/services/utils.py
import os
import uuid
from flask import current_app
from app.database.sqlserver import get_sqlserver_connection  
import getpass

# app/services/utils.py
def allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", set())

def get_os_user():
    return getpass.getuser()

def obtener_datos_elemento(tipo, codigo):
    conn = get_sqlserver_connection()
    cursor = conn.cursor()
#PROTECCION Y CONTROL
    if tipo == 'Proteccion/Control':
        query = """
            SELECT DescripcionOptimus, ProX, ProY, direccion, IdUUNN, Alicodigo, abierto,
                   nombrepropietario, device_type, codtennomimt
            FROM RDP_ProCon WHERE PuntoMedicion = ? and IdEstado = 1
        """
        cursor.execute(query, (codigo,))
        row = cursor.fetchone()
        if row:
            ali_codigo = row[5]
            uunn_id = row[4]

            cursor.execute("SELECT OpCodigo FROM RDP_Alimentador WHERE AliCodigo = ?", (ali_codigo,))
            nombre_ali = cursor.fetchone()
            ali_nombre = nombre_ali[0] if nombre_ali else 'Desconocido'

            cursor.execute("SELECT nombre FROM UnidadNegocio WHERE IdUUNN = ?", (uunn_id,))
            nombre_uunn = cursor.fetchone()
            uunn_nombre = nombre_uunn[0] if nombre_uunn else 'Sin UUNN'

            return {
                'descripcion': row[0],
                'pro_x': row[1],
                'pro_y': row[2],
                'direccion': row[3],
                'uun_id': uunn_id,
                'uun_nombre': uunn_nombre,
                'alicodigo': ali_codigo,
                'ali_nombre': ali_nombre,
                'abierto': row[6],
                'nombre_propietario': row[7],
                'device_type': row[8],
                'codtennomimt': row[9],
            }
#SUBESTACION DISTRIBUCION
    elif tipo == 'Subestacion':
        query = """
            SELECT DescripcionOptimus, SubX, SubY, Direccion, AliCodigo, IdUUNN,
                   nombrepropietario, tensionbt, tensionmt,
                   subconetrabt, potenciainstalada, type
            FROM RDS_Subestacion WHERE SubSubestacion = ? and IdEstado = 1
        """
        cursor.execute(query, (codigo,))
        row = cursor.fetchone()
        if row:
            ali_codigo = row[4]
            uunn_id = row[5]

            cursor.execute("SELECT OpCodigo FROM RDP_Alimentador WHERE AliCodigo = ?", (ali_codigo,))
            nombre_ali = cursor.fetchone()
            ali_nombre = nombre_ali[0] if nombre_ali else 'Desconocido'

            cursor.execute("SELECT nombre FROM UnidadNegocio WHERE IdUUNN = ?", (uunn_id,))
            nombre_uunn = cursor.fetchone()
            uunn_nombre = nombre_uunn[0] if nombre_uunn else 'Sin UUNN'

            return {
                'descripcion': row[0],
                'sub_x': row[1],
                'sub_y': row[2],
                'direccion': row[3],
                'alicodigo': ali_codigo,
                'ali_nombre': ali_nombre,
                'uun_id': uunn_id,
                'uun_nombre': uunn_nombre,
                'nombre_propietario': row[6],
                'tension_bt': row[7],
                'tension_mt': row[8],
                'subconectra_bt': row[9],
                'potencia': row[10],
                'tipo_sub': row[11],
            }
        
#TRANSFORMADOR DE POTENCIA
    elif tipo == 'Subestación de potencia':
        query = """
            SELECT CenNombre, IdUUNN, OpCodigo, CenX, CenY
            FROM dbo.RDP_CentroTransformacion WHERE CenNombre = ? and IdEstado = 1 and TipoPunto <> 'G'
        """
        cursor.execute(query, (codigo,))
        row = cursor.fetchone()
        if row:
            uunn_id = row[1]

            cursor.execute("SELECT nombre FROM UnidadNegocio WHERE IdUUNN = ?", (uunn_id,))
            nombre_uunn = cursor.fetchone()
            uunn_nombre = nombre_uunn[0] if nombre_uunn else 'Sin UUNN'

            return {
                'descripcion': row[0],
                'nombre_trafo': row[0],
                'uun_id': uunn_id,
                'uun_nombre': uunn_nombre,
                'codigo_trafo': row[2],
                'trafo_x': row[3],
                'trafo_y': row[4],
            }

#COMERCIAL - SUMINISTROS

    elif tipo == 'Suministro':
        query = """
            SELECT SumCodigo, AliOpCodigo, SubOpCodigo, CirOpCodigo, CoordenadaX, CoordenadaY, IdUUNN, Direccion
            FROM dbo.comercial WHERE SumCodigo = ?
        """
        cursor.execute(query, (codigo,))
        row = cursor.fetchone()
        if row:
            uunn_id = row[6]
            nombre_ali = row[1]

            cursor.execute("SELECT AliCodigo FROM RDP_Alimentador WHERE OpCodigo = ?", (nombre_ali,))
            codigo_ali = cursor.fetchone()
            ali_codigo = codigo_ali[0] if codigo_ali else 'Desconocido'

            cursor.execute("SELECT nombre FROM UnidadNegocio WHERE IdUUNN = ?", (uunn_id,))
            nombre_uunn = cursor.fetchone()
            uunn_nombre = nombre_uunn[0] if nombre_uunn else 'Sin UUNN'

            return {
                'descripcion': row[0],
                'cod_suministro': row[0],
                'alicodigo':ali_codigo,
                'ali_nombre': row[1],
                'sub_codigo':row[2],
                'circ_codigo':row[3],
                'sum_x': row[4],
                'sum_y': row[5],
                'uun_id': uunn_id,
                'uun_nombre': uunn_nombre,
                'direccion_sum': row[7],

            }
#Estructura MT
    else:
        query = """
            SELECT NodNtcse, AliCodigo, NodX, NodY, IdUUNN, owner_type
            FROM dbo.EST_Poste WHERE NodNtcse = ? and IdEstado = 1 and NodBTMT='M'
        """
        cursor.execute(query, (codigo,))
        row = cursor.fetchone()
        if row:
            ali_codigo = row[1]
            uunn_id = row[4]

            cursor.execute("SELECT OpCodigo FROM RDP_Alimentador WHERE AliCodigo = ?", (ali_codigo,))
            nombre_ali = cursor.fetchone()
            ali_nombre = nombre_ali[0] if nombre_ali else 'Desconocido'

            cursor.execute("SELECT nombre FROM UnidadNegocio WHERE IdUUNN = ?", (uunn_id,))
            nombre_uunn = cursor.fetchone()
            uunn_nombre = nombre_uunn[0] if nombre_uunn else 'Sin UUNN'

            return {
                'descripcion': row[0],
                'cod_poste': row[0],
                'alicodigo': ali_codigo,
                'ali_nombre': ali_nombre,
                'uun_id': uunn_id,
                'uun_nombre': uunn_nombre,
                'poste_x': row[2],
                'poste_y': row[3],
                'owner_type': row[5]
            }

def guardar_evidencia(archivo):
    if archivo and archivo.filename != '':
        ext = archivo.filename.rsplit('.', 1)[-1].lower()
        nombre_archivo = f"{uuid.uuid4().hex}.{ext}"
        ruta = os.path.join(current_app.config['UPLOAD_FOLDER'], nombre_archivo)
        archivo.save(ruta)
        return nombre_archivo
    return None