# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-super-secreta')
    DEBUG = True

    # PostgreSQL para registrar incidencias
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://postgres:enosacco@localhost/interrupciones'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQL Server para autocompletado (usando pyodbc)
    SQLSERVER_CONN_STR = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=SDB10002;'
        'DATABASE=BDIGIS;'
        'TRUSTED_CONNECTION=yes;'
    )

    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app','static','uploads','reporte')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'msg'}

    UPLOAD_REPORTE = "static/uploads/reporte"
    UPLOAD_CIERRE  = "static/uploads/cierre"
