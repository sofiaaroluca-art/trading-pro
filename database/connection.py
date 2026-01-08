"""
Conexión a la base de datos SQLite con SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import sys
sys.path.append('..')
from config import DATABASE_URL

# Motor de base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necesario para SQLite
    echo=False  # Cambiar a True para ver queries SQL en consola
)

# Sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()


def get_db() -> Session:
    """
    Generador de sesiones de base de datos.
    Usar con: with get_db() as db: ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    """
    from database.models import Base
    Base.metadata.create_all(bind=engine)
    print("✅ Base de datos inicializada correctamente")
