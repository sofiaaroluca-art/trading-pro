"""
Configuración central del sistema de trading
"""
import os
from pathlib import Path

# Directorio base
BASE_DIR = Path(__file__).parent

# ==================== API KEYS ====================
# TwelveData - Para datos históricos y velas
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "4482ac6740914afe884d709c9c132fff")

# Finnhub - Para datos en TIEMPO REAL (WebSocket gratuito)
# Obtener gratis en: https://finnhub.io/register
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "d5g9dg9r01qie3lha70gd5g9dg9r01qie3lha710")

# Base de datos
DATABASE_URL = f"sqlite:///{BASE_DIR}/trading.db"

# Pares de divisas disponibles para trading
FOREX_PAIRS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "AUD/USD",
    "USD/CAD",
    "EUR/GBP",
    "EUR/JPY",
    "GBP/JPY",
]

# Configuración de indicadores técnicos
INDICATORS_CONFIG = {
    "rsi": {
        "period": 14,
        "overbought": 70,
        "oversold": 30,
    },
    "macd": {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
    },
    "bollinger": {
        "period": 20,
        "std_dev": 2,
    },
    "sma": {
        "periods": [10, 20, 50],
    },
    "ema": {
        "periods": [9, 21, 55],
    },
}

# Configuración de señales
SIGNAL_CONFIG = {
    # Mínimo de indicadores que deben coincidir para generar señal
    "min_confirmations": 2,
    # Fuerza mínima de señal (0-100)
    "min_strength": 60,
}

# Configuración del servidor
SERVER_CONFIG = {
    "host": "127.0.0.1",
    "port": 8000,
}

# Intervalos de tiempo disponibles
TIMEFRAMES = ["1min", "5min", "15min", "30min", "1h", "4h", "1day"]

# Intervalo por defecto para análisis
DEFAULT_TIMEFRAME = "1min"

# Número de velas a obtener para análisis
CANDLES_LIMIT = 100
