# app/models.py
from datetime import datetime

from flask_login     import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


# ------------------------------------------------------------------ #
#  TABLA INTERMEDIA (many-to-many área  ←→  tipo de incidencia)
# ------------------------------------------------------------------ #
tipo_incidencia_area = db.Table(
    "tipo_incidencia_area",
    db.Column("tipo_incidencia_id",
              db.Integer,
              db.ForeignKey("tipos_incidencias.id")),
    db.Column("area_responsable_id",
              db.Integer,
              db.ForeignKey("areas_responsables.id")),
)


# ------------------------------------------------------------------ #
#  ÁREA RESPONSABLE
# ------------------------------------------------------------------ #
class AreaResponsable(db.Model):
    __tablename__ = "areas_responsables"

    id               = db.Column(db.Integer, primary_key=True)
    area_responsable = db.Column(db.String(10), unique=True, nullable=False)
    nombre_area      = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<AreaResponsable {self.area_responsable}>"


# ------------------------------------------------------------------ #
#  USUARIO
# ------------------------------------------------------------------ #
class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id       = db.Column(db.Integer, primary_key=True)
    nombre   = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, index=True)
    _pw_hash = db.Column("pw_hash", db.String(128))
    rol      = db.Column(db.String(20), default="Responsable")        # Admin/Responsable/Visitante

    id_area  = db.Column(db.Integer, db.ForeignKey("areas_responsables.id"))
    area     = db.relationship("AreaResponsable", backref="usuarios")

    # ---------- helpers ----------
    def set_password(self, raw: str) -> None:
        self._pw_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self._pw_hash, raw)

    def is_admin(self) -> bool:
        return self.rol.lower() == "admin"

    def can_edit(self) -> bool:
        """¿Puede crear / cerrar incidencias?"""
        return self.rol.lower() in ("admin", "responsable")

    def __repr__(self):
        return f"<Usuario {self.username}>"


# ------------------------------------------------------------------ #
#  TIPO DE INCIDENCIA
# ------------------------------------------------------------------ #
class TipoIncidencia(db.Model):
    __tablename__ = "tipos_incidencias"

    id             = db.Column(db.Integer, primary_key=True)
    tipoincidencia = db.Column(db.String(80), nullable=False)
    peso_tipo      = db.Column(db.Float, default=1.0)

    areas_responsables = db.relationship(
        "AreaResponsable",
        secondary=tipo_incidencia_area,
        backref="tipos_incidencias",
    )

    def __repr__(self):
        return f"<TipoIncidencia {self.tipoincidencia}>"


# ------------------------------------------------------------------ #
#  REGISTRO DE INCIDENCIA
# ------------------------------------------------------------------ #
class RegIncidencia(db.Model):
    __tablename__ = "reg_incidencias"

    id                = db.Column(db.Integer, primary_key=True)
    tipo_elemento     = db.Column(db.String(50),  nullable=False)
    codigo_elemento   = db.Column(db.String(50),  nullable=False)
    descripcion_elemento = db.Column(db.String(200))

    # Coordenadas (opcional)
    coord_x_inicio = db.Column(db.Float)
    coord_y_inicio = db.Column(db.Float)
    coord_x_fin    = db.Column(db.Float)
    coord_y_fin    = db.Column(db.Float)
    
    # Relaciones clave-foránea
    tipo_id = db.Column(db.Integer, db.ForeignKey("tipos_incidencias.id"))
    tipo    = db.relationship("TipoIncidencia")

    responsable_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    responsable    = db.relationship("Usuario", backref="incidencias")

    area_responsable_id = db.Column(db.Integer, db.ForeignKey("areas_responsables.id"))
    area_responsable    = db.relationship("AreaResponsable")

    # Metadatos
    fecha_reporte      = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_windows    = db.Column(db.String(50), nullable=False)
    ocurrencia         = db.Column(db.Text,  nullable=False)
    estado             = db.Column(db.String(20), default="Abierto")
    fecha_levantamiento = db.Column(db.DateTime)
    tareas_cierre      = db.Column(db.Text)

    alicodigo = db.Column(db.String(50))

    # --- Relación 1-N: evidencias del REPORTE ---
    evidencias = db.relationship(
        "EvidenciaIncidencia",
        back_populates="incidencia",
        cascade="all, delete-orphan",
    )

    # --- Relación 1-N: evidencias del CIERRE ---
    evidencias_cierre = db.relationship(
        "EvidenciaCierre",
        back_populates="incidencia",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Incidencia {self.id} – {self.codigo_elemento}>"


# ------------------------------------------------------------------ #
#  EVIDENCIA (reporte)
# ------------------------------------------------------------------ #
class EvidenciaIncidencia(db.Model):
    __tablename__ = "evidencias_incidencias"

    id = db.Column(db.Integer, primary_key=True)
    incidencia_id = db.Column(
        db.Integer,
        db.ForeignKey("reg_incidencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename    = db.Column(db.String(200), nullable=False)
    filepath    = db.Column(db.String(300), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    incidencia = db.relationship(
        "RegIncidencia",
        back_populates="evidencias",
    )

    def __repr__(self):
        return f"<EvidenciaReporte {self.filename} → Inc {self.incidencia_id}>"


# ------------------------------------------------------------------ #
#  EVIDENCIA (cierre)
# ------------------------------------------------------------------ #
class EvidenciaCierre(db.Model):
    __tablename__ = "evidencias_cierre"

    id = db.Column(db.Integer, primary_key=True)
    incidencia_id = db.Column(
        db.Integer,
        db.ForeignKey("reg_incidencias.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename    = db.Column(db.String(200), nullable=False)
    filepath    = db.Column(db.String(300), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    incidencia = db.relationship(
        "RegIncidencia",
        back_populates="evidencias_cierre",
    )

    def __repr__(self):
        return f"<EvidenciaCierre {self.filename} → Inc {self.incidencia_id}>"
