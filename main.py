"""
SISTEMA TRADING PRO - Servidor Principal
=========================================
Backend con FastAPI para sistema de trading Forex
"""
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from config import SERVER_CONFIG
from database.connection import init_db
from api.routes import router
from api.websocket_manager import websocket_handler

# Crear aplicación FastAPI
app = FastAPI(
    title="Sistema Trading PRO",
    description="Sistema de trading con señales automáticas para Forex",
    version="1.0.0",
    docs_url="/docs",      # Documentación Swagger
    redoc_url="/redoc",    # Documentación ReDoc
)

# Configurar CORS para permitir conexiones del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos (CSS, JS, imágenes)
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Incluir rutas de la API
app.include_router(router, prefix="/api", tags=["Trading API"])


# ==================== RUTAS PRINCIPALES ====================

@app.get("/", include_in_schema=False)
async def root():
    """Sirve la página principal"""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Sistema Trading PRO - API activa", "docs": "/docs"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para datos en tiempo real"""
    await websocket_handler(websocket)


# ==================== EVENTOS DE INICIO ====================

@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar el servidor"""
    print("=" * 50)
    print("🚀 SISTEMA TRADING PRO - Iniciando...")
    print("=" * 50)
    
    # Inicializar base de datos
    try:
        init_db()
    except Exception as e:
        print(f"⚠️ Error inicializando BD: {e}")
    
    print(f"📡 API disponible en: http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
    print(f"📚 Documentación: http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}/docs")
    print(f"🔌 WebSocket: ws://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}/ws")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """Se ejecuta al cerrar el servidor"""
    print("\n🛑 Cerrando Sistema Trading PRO...")


# ==================== PUNTO DE ENTRADA ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
        reload=False,  # Desactivar reload para evitar reinicios
        log_level="info"
    )
