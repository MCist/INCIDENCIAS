# app/api/incidencias_api.py 
from flask import Blueprint, request, jsonify, current_app
from app.models import db, RegIncidencia, EvidenciaCierre, TipoIncidencia
from datetime import datetime
from werkzeug.utils import secure_filename
import os, uuid
from config import Config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.database.sqlserver import get_sqlserver_connection
from app.services.incident_service import update_incidencia

limiter = Limiter(key_func=get_remote_address)
incidencias_api = Blueprint(
    "incidencias_api", __name__, url_prefix="/api/incidencias"
)

ALLOWED_EXTS  = Config.ALLOWED_EXTENSIONS
UPLOAD_FOLDER = Config.UPLOAD_CIERRE


def allowed_file(fname):
    return "." in fname and fname.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


# ------------------------------------------------------------------ #
# 1) Listado para DataTables
# ------------------------------------------------------------------ #
@incidencias_api.route("/data")

def lista_json():
    q = (db.session
           .query(RegIncidencia)
           .join(TipoIncidencia, RegIncidencia.tipo_id == TipoIncidencia.id))
    # ----------------------- filtros ---------------------------------
    estado = request.args.get("estado")
    resp   = request.args.get("responsable")
    ali    = request.args.get("ali")
    crit = request.args.get("crit")
    f_ini  = request.args.get("f_ini")
    f_fin  = request.args.get("f_fin")
    search_term = request.args.get("search[value]")

    if estado: q = q.filter(RegIncidencia.estado == estado)
    if resp  : q = q.filter(RegIncidencia.responsable_id == int(resp))
    if ali   : q = q.filter(RegIncidencia.alicodigo == ali)
    if f_ini : q = q.filter(RegIncidencia.fecha_reporte >=
                            datetime.fromisoformat(f_ini))
    if f_fin : q = q.filter(RegIncidencia.fecha_reporte <=
                            datetime.fromisoformat(f_fin))
    if search_term:
        q = q.filter(RegIncidencia.codigo_elemento.ilike(f"%{search_term}%"))
    if crit:
        bounds = {"alta":0.85, "media":0.70, "baja":0.50, "leve":0.0}[crit]
        q = q.filter(TipoIncidencia.peso_tipo >= bounds)
        if crit != "alta":                       # limite superior
            upper = {"media":0.85, "baja":0.70, "leve":0.50}[crit]
            q = q.filter(TipoIncidencia.peso_tipo < upper)
    # --------------------- ordenamiento ------------------------------
    order_col = request.args.get("order_col", "fecha")
    order_dir = request.args.get("order_dir", "desc")

    col_map = {
        "id"        : RegIncidencia.id,
        "codigo"    : RegIncidencia.codigo_elemento,
        "desc"      : RegIncidencia.descripcion_elemento,
        "area"      : RegIncidencia.area_responsable_id,
        "tipo"      : TipoIncidencia.tipoincidencia,
        "criticidad": TipoIncidencia.peso_tipo,
        "estado"    : RegIncidencia.estado,
        "fecha"     : RegIncidencia.fecha_reporte,
    }

    sort_expr = col_map.get(order_col, RegIncidencia.fecha_reporte)
    q = q.order_by(sort_expr.desc() if order_dir == "desc" else sort_expr.asc())

    # -------------------- paginación ---------------------------------
    start  = int(request.args.get("start", 0))
    length = int(request.args.get("length", 10))
    total  = q.count()

    data = (q.offset(start).limit(length).all())
    ali_codes = {str(i.alicodigo) for i in data if i.alicodigo}
    alias = {}
    if ali_codes:
        try:
            conn = get_sqlserver_connection()
            cur  = conn.cursor()
            cur.execute(f"""
              SELECT AliCodigo, OpCodigo
                FROM RDP_Alimentador
               WHERE AliCodigo IN ({','.join(ali_codes)})
            """)
            alias = {str(r[0]): r[1] for r in cur.fetchall()}
        except Exception as e:
            current_app.logger.warning("Alias alimentador: %s", e)
    # ---------------------- JSON -------------------------------------
    rows = [{
        "id"        : inc.id,
        "codigo"    : inc.codigo_elemento,
        "ali"       : alias.get(str(inc.alicodigo), "") if inc.alicodigo else "",
        "desc"      : inc.descripcion_elemento,
        "area"      : inc.area_responsable.nombre_area if inc.area_responsable else "",
        "tipo"      : inc.tipo.tipoincidencia,
        "criticidad": inc.tipo.peso_tipo,
        "estado"    : inc.estado,
        "fecha"     : inc.fecha_reporte.strftime("%Y-%m-%d %H:%M"),
    } for inc in data]

    return jsonify({
        "recordsTotal"   : total,
        "recordsFiltered": total,
        "data"           : rows,
    })


# ------------------------------------------------------------------ #
# 2) Cierre / levantamiento
# ------------------------------------------------------------------ #
@incidencias_api.route("/<int:inc_id>/cerrar", methods=["POST"])
@limiter.limit("3 per minute")
def cerrar_incidencia(inc_id):
    inc = RegIncidencia.query.get_or_404(inc_id)
    if inc.estado == "Cerrado":       # seguridades extra
        return jsonify({"error": "Ya está cerrada"}), 409

    # texto
    inc.tareas_cierre       = request.form.get("tareas_cierre", "")
    inc.estado              = "Cerrado"
    inc.fecha_levantamiento = datetime.utcnow()

    # archivo
    files = request.files.getlist("evidencia")
    for f in files:
        if not f or not f.filename or not allowed_file(f.filename):
            continue
        ext   = f.filename.rsplit(".", 1)[1].lower()
        fname = f"{inc_id}_{uuid.uuid4().hex}.{ext}"
        save_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(save_dir, exist_ok=True)
        f.save(os.path.join(save_dir, fname))

        db.session.add(EvidenciaCierre(
            incidencia_id = inc_id,
            filename      = secure_filename(f.filename),
            filepath      = fname
        ))

    db.session.commit()
    return jsonify({"msg": "Incidencia cerrada"}), 200

@incidencias_api.route("/<int:inc_id>/detalle")
def detalle_incidencia(inc_id):
    inc = RegIncidencia.query.get_or_404(inc_id)

    rep_imgs = [f'<a href="/static/uploads/reporte/{e.filepath}" target="_blank">ver</a>'
                for e in inc.evidencias] or []
    cie_imgs = [f'<a href="/static/uploads/cierre/{e.filepath}" target="_blank">ver</a>'
                for e in inc.evidencias_cierre] or []

    return jsonify({
        "ocurrencia"     : inc.ocurrencia,
        "tareas_cierre"  : inc.tareas_cierre,
        "f_rep"          : inc.fecha_reporte.strftime("%Y-%m-%d %H:%M"),
        "f_cie"          : inc.fecha_levantamiento and
                           inc.fecha_levantamiento.strftime("%Y-%m-%d %H:%M"),
        "img_rep"        : '<br>'.join(rep_imgs),
        "img_cie"        : '<br>'.join(cie_imgs)
    })
@incidencias_api.route("/alimentadores")
def lista_alimentadores():
    # 1) obtenemos los códigos que de verdad existen en la tabla de incidencias
    ali_rows = (db.session.query(RegIncidencia.alicodigo)
                         .filter(RegIncidencia.alicodigo.isnot(None))
                         .distinct()
                         .all())
    ali_codigos = [str(r[0]) for r in ali_rows]
    if not ali_codigos:
        return jsonify([])

    # 2) pedimos los nombres a SQL-Server de un solo viaje
    conn   = get_sqlserver_connection()
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(ali_codigos))
    cursor.execute(f"""
        SELECT AliCodigo, OpCodigo
        FROM   RDP_Alimentador
        WHERE  AliCodigo IN ({placeholders})
    """, ali_codigos)
    rows = cursor.fetchall()
    mapping = { str(r[0]): r[1] for r in rows }

    # 3) devolvemos  lista de objetos  [{value:..., label:...}, …]
    payload = [{"value": c, "label": mapping.get(c, c)}
               for c in sorted(ali_codigos)]

    return jsonify(payload)

@incidencias_api.route('/<int:id>', methods=['PUT', 'POST'])
def api_update_incidencia(id):
    form = request.form
    files = request.files
    incidencia, err = update_incidencia(id, form, files)
    if err:
        return jsonify({'error': err}), 400
    return jsonify({'ok': True, 'id': incidencia.id})