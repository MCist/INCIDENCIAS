"""
Genera un GeoJSON comprimido con todos los vanos de la red eléctrica.
Se ejecuta a diario desde APScheduler (ver app/__init__.py).
"""
import json, gzip, pathlib, datetime
from app.database.sqlserver import get_sqlserver_connection

def generate_redes_geojson() -> None:
    print("⏳ Generando red eléctrica…")
    conn = get_sqlserver_connection()
    cur  = conn.cursor()
    cur.execute(
        """
        SELECT  VanCodigo,
                VanVano,
                IdUUNN,
                alioptimus,
                VanX1, VanY1,
                VanX2, VanY2
        FROM dbo.RDP_Vano
        WHERE IdEstado = 1
        """
    )

    features = []
    for van_cod, vano, id_uunn, ali_opt, x1, y1, x2, y2 in cur:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[x1, y1], [x2, y2]],   # [lon, lat]
                },
                "properties": {
                    "van": van_cod,
                    "vano": vano,
                    "alimentador": ali_opt,
                    "uun": id_uunn,
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}

    # Ruta …/app/static/data/
    project_root = pathlib.Path(__file__).resolve().parents[1]    # …/CONSULTAS
    out_dir = project_root / "static" / "data"

    out_dir.mkdir(parents=True, exist_ok=True)

    with gzip.open(out_dir / "redes.geojson.gz", "wt", encoding="utf-8") as f:
        json.dump(geojson, f, separators=(",", ":"))

    print(f"✅ Red generada ({len(features):,} tramos) → {out_dir/'redes.geojson.gz'}")
