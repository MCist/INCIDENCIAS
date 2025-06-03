#init_db.py
from app import create_app, db
from app import models
from app.models import EvidenciaIncidencia

app = create_app()

with app.app_context():
    print("📌 Base de datos actual:", db.engine.url.database)
    print("📦 Tablas que se crearán:", db.metadata.tables.keys())
    confirm = input("⚠️ Esto eliminará todas las tablas del modelo actual. ¿Continuar? (s/n): ")
    if confirm.lower() == 's':
        db.drop_all()
        print("🗑️ Tablas anteriores eliminadas.")
        db.create_all()
        print("✅ Tablas creadas exitosamente.")

    # Verifica si las áreas ya existen para evitar duplicados
    if not models.AreaResponsable.query.first():
        print("📝 Insertando áreas responsables...")

        umd = models.AreaResponsable(area_responsable="UMD", nombre_area="Unidad Mantenimiento de Distribución")
        umt = models.AreaResponsable(area_responsable="UMT", nombre_area="Unidad Mantenimiento de Transmisión")

        db.session.add_all([umd, umt])
        db.session.commit()

        print("✅ Áreas responsables insertadas.")
    else:
        umd = models.AreaResponsable.query.filter_by(area_responsable="UMD").first()
        umt = models.AreaResponsable.query.filter_by(area_responsable="UMT").first()

    # Verifica si ya existen tipos de incidencia
    if not models.TipoIncidencia.query.first():
        print("📝 Insertando tipos de incidencia...")

        tipos_incidencias = [
            ("Llave termomagnética con bypass", [umd], 0.8),
            ("Fuga de aceite en trafo de distribución", [umd], 1),
            ("Fuga de aceite en trafo de potencia", [umt], 1),
            ("Relé apagado", [umt],1),
            ("Medidor apagado", [umt],0.8),
            ("Control de recloser apagado", [umd, umt], 1),
            ("Batería de recloser averiada", [umd, umt], 1),
            ("Circuito BT conectado directo a barra", [umd], 0.8),
            ("Cut-out con bypass", [umd], 0.8),
            ("Cuchillas con bypass", [umd, umt], 0.8),
            ("Punto caliente", [umd, umt], 0.9),
            ("Enlace MT inoperativo", [umd, umt], 0.9),
            ("Interruptor de potencia en celda MT averiado", [umt], 1),
            ("Interrupto de potencia en patio averiado", [umt], 1),
            ("Trafo zigzag averiado", [umt], 1),
            ("Banco de condensadores averiado", [umt], 0.8),
            ("Relé desconfigurado", [umt], 1),
            ("Recloser desconfigurado", [umt], 1),
            ("Regulador de tensión en SET averiado o desconfigurado", [umt], 1),
            ("Banco de condensadores desconectados", [umt], 0.6),
            ("Banco de reguladores en red desconectados", [umt], 0.6),
            ("Reflectores en patio apagados", [umt], 0.5),
            ("Tablero de control de SED sin puerta", [umd], 0.8),
            ("Otros (infraestructura civil, electromecánico, orden y limpieza)",[umd, umt], 1.0)
        ]

        for nombre, areas, peso in tipos_incidencias:
            tipo = models.TipoIncidencia(tipoincidencia=nombre, peso_tipo = peso)
            tipo.areas_responsables.extend(areas)
            db.session.add(tipo)

        db.session.commit()
        print("✅ Tipos de incidencia insertados.")

    else:
        print("ℹ️ Tipos de incidencia ya están registrados.")

    # Verifica si ya existen usuarios
    if not models.Usuario.query.first():
        print("👤 Insertando usuarios de prueba...")

        usuario1 = models.Usuario(
            nombre="Jefatura UMD",
            username="jumd",
            id_area=umd.id,
            rol="Responsable"
        )

        usuario2 = models.Usuario(
            nombre="Jefatura UMT",
            username="jumt",
            id_area=umt.id,
            rol="Responsable"
        )

        db.session.add_all([usuario1, usuario2])
        db.session.commit()
        print("✅ Usuarios insertados.")
    else:
        print("ℹ️ Ya existen usuarios registrados.")

