# app/db/sqlserver.py
import pyodbc
from config import Config

def get_sqlserver_connection():
    return pyodbc.connect(Config.SQLSERVER_CONN_STR)
