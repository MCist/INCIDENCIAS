# app/api/dashboard_api.py

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models import RegIncidencia, TipoIncidencia
from app.database.sqlserver import get_sqlserver_connection
from app.api.incidencias_api import lista_alimentadores

dashboard_api = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")

@dashboard_api.route("", methods=["GET"])
def summary():
    # 1) Leer filtros
    estado = request.args.get("estado")
    area   = request.args.get("area", type=int)
    ali    = request.args.get("alimentador")
    crit   = request.args.get("criticidad")
    antig  = request.args.get("antiguedad")  # “”, “hoy”, “7”, “15”, “30”

    filtros = []
    if estado: filtros.append(RegIncidencia.estado == estado)
    if area:   filtros.append(RegIncidencia.area_responsable_id == area)
    if ali:    filtros.append(RegIncidencia.alicodigo == ali)

    # 2) Criticidad
    if crit == "alta":
        filtros.append(TipoIncidencia.peso_tipo >= 0.85)
    elif crit == "media":
        filtros.extend([
            TipoIncidencia.peso_tipo >= 0.70,
            TipoIncidencia.peso_tipo <  0.85
        ])
    elif crit == "baja":
        filtros.extend([
            TipoIncidencia.peso_tipo >= 0.50,
            TipoIncidencia.peso_tipo <  0.70
        ])
    elif crit == "leve":
        filtros.append(TipoIncidencia.peso_tipo <  0.50)

    # 3) Antigüedad
    if antig:
        now = datetime.utcnow()
        if antig == "hoy":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            filtros.extend([
                RegIncidencia.fecha_reporte >= start,
                RegIncidencia.fecha_reporte <= now
            ])
        elif antig in ("7", "15"):
            dias = int(antig)
            filtros.extend([
                RegIncidencia.fecha_reporte >= now - timedelta(days=dias),
                RegIncidencia.fecha_reporte <= now
            ])
        elif antig == "30":
            filtros.append(RegIncidencia.fecha_reporte <= now - timedelta(days=30))

    # 4) Base query para KPIs
    base_q = db.session.query(RegIncidencia).join(TipoIncidencia).filter(*filtros)

    # — total y abierto/cerrado
    total = base_q.count()
    sub   = base_q.with_entities(RegIncidencia.estado, func.count()).group_by(RegIncidencia.estado).all()
    counts = {est: cnt for est, cnt in sub}
    abierto, cerrado = counts.get("Abierto", 0), counts.get("Cerrado", 0)

    # — MTTR global (h)
    mttr_list = [
        (inc.fecha_levantamiento - inc.fecha_reporte).total_seconds()/3600
        for inc in base_q
            .filter(RegIncidencia.estado=="Cerrado",
                    RegIncidencia.fecha_levantamiento.isnot(None))
            .all()
    ]
    mttr_h = round(sum(mttr_list)/len(mttr_list), 2) if mttr_list else 0.0

    # — criticidad global
    crit_raw = (
        db.session.query(TipoIncidencia.peso_tipo, func.count())
          .join(RegIncidencia)
          .filter(RegIncidencia.id.in_(base_q.with_entities(RegIncidencia.id)))
          .group_by(TipoIncidencia.peso_tipo)
          .all()
    )
    crit_data = {"alta":0,"media":0,"baja":0,"leve":0}
    for peso, cnt in crit_raw:
        lvl = ("alta" if peso>=0.85
               else "media" if peso>=0.7
               else "baja"  if peso>=0.5
               else "leve")
        crit_data[lvl] += cnt

    # Armar response inicial con KPIs
    response = {
        "kpi": {
            "total": total,
            "abierto": abierto,
            "cerrado": cerrado,
            "mttr_h": mttr_h,
            "criticidad": crit_data
        }
    }

    # 5a) GLOBAL: incidencias apiladas por alimentador
    if not ali:
        alim_counts = (
            db.session.query(
                RegIncidencia.alicodigo,
                TipoIncidencia.peso_tipo,
                func.count().label("cnt")
            )
            .join(TipoIncidencia)
            .filter(RegIncidencia.alicodigo.isnot(None), *filtros)
            .group_by(RegIncidencia.alicodigo, TipoIncidencia.peso_tipo)
            .all()
        )
        # Extraer códigos únicos y ordenarlos
        codes = sorted({row.alicodigo for row in alim_counts})

        # Usar la API de alimentadores para mapear a nombres
        alias_list = lista_alimentadores().get_json()
        alias_map  = {item['value']: item['label'] for item in alias_list}

        labels = [alias_map.get(str(c), str(c)) for c in codes]

        # Construir datasets apilados (4 niveles fijos)
        niveles = [
            ("alta",  0.85, "#dc3545"),
            ("media", 0.70, "#fd7e14"),
            ("baja",  0.50, "#ffc107"),
            ("leve",  0.00, "#198754"),
        ]
        datasets = []
        for lvl, low, color in niveles:
            data = []
            for c in codes:
                cnt = sum(
                    r.cnt for r in alim_counts
                    if r.alicodigo == c and (
                        (lvl=="alta"  and r.peso_tipo>=0.85) or
                        (lvl=="media" and 0.70<=r.peso_tipo<0.85) or
                        (lvl=="baja"  and 0.50<=r.peso_tipo<0.70) or
                        (lvl=="leve"  and r.peso_tipo<0.50)
                    )
                )
                data.append(cnt)
            datasets.append({
                "label": lvl.capitalize(),
                "data": data,
                "backgroundColor": color
            })

        response["por_alimentador"] = {
            "labels": labels,
            "datasets": datasets
        }

    # 5b) ÚNICO ALIMENTADOR: distribución y MTTR por tipo
    else:
        # Conteo por tipo
        cnt_tipo = (
            db.session.query(
                TipoIncidencia.tipoincidencia,
                TipoIncidencia.peso_tipo,
                func.count().label("cnt")
            )
            .join(RegIncidencia)
            .filter(RegIncidencia.alicodigo==ali, *filtros)
            .group_by(TipoIncidencia.tipoincidencia, TipoIncidencia.peso_tipo)
            .all()
        )
        # helper de color
        def color_for(p):
            if p>=0.85: return "#dc3545"
            if p>=0.70: return "#fd7e14"
            if p>=0.50: return "#ffc107"
            return "#198754"

        labels_t = [r.tipoincidencia for r in cnt_tipo]
        data_t   = [r.cnt           for r in cnt_tipo]
        colors_t = [color_for(r.peso_tipo) for r in cnt_tipo]
        response["por_tipo"] = {
            "labels": labels_t,
            "datasets": [{
                "label": "Incidencias",
                "data": data_t,
                "backgroundColor": colors_t
            }]
        }

        # MTTR por tipo
        mttr_labels, mttr_data = [], []
        for tipo_name, peso, _ in cnt_tipo:
            diffs = [
                (inc.fecha_levantamiento - inc.fecha_reporte).total_seconds()/3600
                for inc in base_q
                    .filter(
                        RegIncidencia.alicodigo==ali,
                        RegIncidencia.estado=="Cerrado",
                        RegIncidencia.tipo.has(tipoincidencia=tipo_name)
                    )
                    .all()
            ]
            mttr_labels.append(tipo_name)
            mttr_data.append(round(sum(diffs)/len(diffs),2) if diffs else 0)

        response["mttr_por_tipo"] = {
            "labels": mttr_labels,
            "datasets": [{
                "label": "MTTR (h)",
                "data": mttr_data,
                "backgroundColor": "#36A2EB"
            }]
        }

    return jsonify(response)
