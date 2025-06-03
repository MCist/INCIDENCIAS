# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from pytz import timezone
from config import Config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

db = SQLAlchemy()
scheduler = APScheduler()
# --------------------------------------------------------------------- #
#  Factory principal
# --------------------------------------------------------------------- #
def create_app() -> Flask:
    """Crea y configura la app Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # ---- Inicializar extensiones ----
    db.init_app(app)
    limiter.init_app(app)
    scheduler.init_app(app)

    # ---- Registrar blueprints ----
    from app.routes.home        import home_bp
    from app.routes.reportar    import reportar_bp
    from app.routes.mapa       import mapa_bp
    from app.routes.incidencias import incidencias_bp
    from app.api.incident_api   import incident_api
    from app.api.incidencias_api  import incidencias_api
    from app.routes.dashboard   import dashboard_bp
    from app.api.dashboard_api import dashboard_api
    from app.routes.metrics   import bp as metrics_bp
    from app.routes.analysis  import bp as analysis_bp
    from app.routes.calls     import bp as calls_bp
    from app.routes.demandas  import bp as demandas_bp
    
    app.register_blueprint(dashboard_api)
    app.register_blueprint(home_bp)
    app.register_blueprint(reportar_bp)
    app.register_blueprint(mapa_bp)
    app.register_blueprint(incidencias_bp)
    app.register_blueprint(incident_api)
    app.register_blueprint(incidencias_api)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(calls_bp)
    app.register_blueprint(demandas_bp)

    # ----------------------------------------------------------------- #
    #  Tareas programadas (APScheduler)
    # ----------------------------------------------------------------- #
    from app.tasks.generate_redes_geojson import generate_redes_geojson


    lima_tz = timezone("America/Lima")

    # Ejecutar todos los días a las 17:30 (hora Perú)
    scheduler.add_job(
        id="regen_redes",
        func=generate_redes_geojson,
        trigger="cron",
        hour=17,
        minute=30,
        timezone=lima_tz,
        replace_existing=True,
    )
    from flask import current_app, send_from_directory

    @app.route("/data/redes.geojson")
    def redes_geojson():
        """Devuelve redes.geojson.gz como JSON gzip‑encoded."""
        response = send_from_directory(
            current_app.static_folder + "/data",
            "redes.geojson.gz",
            mimetype="application/json",
            conditional=True,
            max_age=86400            # 1 día
        )
        response.headers["Content-Encoding"] = "gzip"
        return response

    scheduler.start()
    return app
