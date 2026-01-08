"""
API Routes - Endpoints para el sistema de trading
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import sys
sys.path.append('..')
from config import FOREX_PAIRS, TIMEFRAMES, DEFAULT_TIMEFRAME
from services.data_service import TwelveDataService
from services.indicators_service import TechnicalIndicators
from services.signal_service import SignalGenerator


# Router principal
router = APIRouter()

# Instancias de servicios
data_service = TwelveDataService()
indicators = TechnicalIndicators()
signal_generator = SignalGenerator()


# ==================== MODELOS PYDANTIC ====================

class PriceResponse(BaseModel):
    symbol: str
    price: float
    timestamp: str


class CandleResponse(BaseModel):
    datetime: str
    open: float
    high: float
    low: float
    close: float


class IndicatorResponse(BaseModel):
    value: float
    signal: str
    extra: dict = None


class AnalysisResponse(BaseModel):
    symbol: str
    timeframe: str
    price: float
    timestamp: str
    indicators: dict
    summary: dict


class SignalResponse(BaseModel):
    symbol: str
    signal_type: str
    strength: float
    price: float
    timestamp: str
    indicators: dict
    confirmations: List[str]
    notes: str


# ==================== ENDPOINTS DE DATOS ====================

@router.get("/pairs", response_model=List[str])
async def get_available_pairs():
    """Obtiene lista de pares de divisas disponibles"""
    return FOREX_PAIRS


@router.get("/timeframes", response_model=List[str])
async def get_available_timeframes():
    """Obtiene intervalos de tiempo disponibles"""
    return TIMEFRAMES


@router.get("/price/{symbol:path}")
async def get_price(symbol: str):
    """
    Obtiene precio actual de un par
    
    - **symbol**: Par de divisas (ej: EUR/USD)
    """
    try:
        result = data_service.get_price(symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices")
async def get_all_prices(
    symbols: Optional[str] = Query(None, description="Pares separados por coma")
):
    """
    Obtiene precios de múltiples pares
    
    - **symbols**: Lista de pares separados por coma (opcional, usa solo EUR/USD por defecto para ahorrar API)
    """
    try:
        # Por defecto solo EUR/USD para ahorrar API credits (8/minuto límite)
        if symbols:
            symbol_list = symbols.split(",")
        else:
            symbol_list = ["EUR/USD"]  # Solo 1 par por defecto
        
        result = data_service.get_multiple_prices(symbol_list)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{symbol:path}")
async def get_quote(symbol: str):
    """
    Obtiene cotización completa de un par
    """
    try:
        result = data_service.get_quote(symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candles/{symbol:path}")
async def get_candles(
    symbol: str,
    interval: str = Query(DEFAULT_TIMEFRAME, description="Intervalo de tiempo"),
    limit: int = Query(100, description="Número de velas", ge=1, le=500)
):
    """
    Obtiene velas históricas
    
    - **symbol**: Par de divisas
    - **interval**: 1min, 5min, 15min, 30min, 1h, 4h, 1day
    - **limit**: Número de velas (1-500)
    """
    try:
        df = data_service.get_candles(symbol, interval, limit)
        candles = df.to_dict(orient="records")
        
        # Convertir datetime a string
        for candle in candles:
            if "datetime" in candle:
                candle["datetime"] = candle["datetime"].isoformat()
        
        return {
            "symbol": symbol,
            "interval": interval,
            "count": len(candles),
            "candles": candles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE ANÁLISIS ====================

@router.get("/analysis/{symbol:path}")
async def get_analysis(
    symbol: str,
    interval: str = Query(DEFAULT_TIMEFRAME, description="Intervalo de tiempo"),
    limit: int = Query(100, description="Número de velas para análisis")
):
    """
    Obtiene análisis técnico completo de un par
    
    - **symbol**: Par de divisas
    - **interval**: Intervalo de tiempo
    """
    try:
        # Obtener datos
        df = data_service.get_candles(symbol, interval, limit)
        
        # Analizar
        summary = indicators.get_analysis_summary(df)
        
        return {
            "symbol": symbol,
            "timeframe": interval,
            **summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis-all")
async def get_analysis_all(
    interval: str = Query(DEFAULT_TIMEFRAME, description="Intervalo de tiempo"),
    limit: int = Query(100, description="Número de velas para análisis")
):
    """
    Obtiene análisis técnico de todos los pares
    """
    try:
        results = {}
        
        for symbol in FOREX_PAIRS:
            try:
                df = data_service.get_candles(symbol, interval, limit)
                summary = indicators.get_analysis_summary(df)
                results[symbol] = {
                    "symbol": symbol,
                    "timeframe": interval,
                    **summary
                }
            except Exception as e:
                results[symbol] = {"error": str(e)}
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE SEÑALES ====================

@router.get("/signal/{symbol:path}")
async def get_signal(
    symbol: str,
    interval: str = Query(DEFAULT_TIMEFRAME, description="Intervalo de tiempo"),
    limit: int = Query(100, description="Número de velas para análisis")
):
    """
    Genera señal de trading para un par
    
    - **symbol**: Par de divisas
    - **interval**: Intervalo de tiempo
    """
    try:
        # Obtener datos
        df = data_service.get_candles(symbol, interval, limit)
        
        # Generar señal
        signal = signal_generator.analyze_for_signal(df, symbol)
        
        if signal:
            return signal_generator.signal_to_dict(signal)
        else:
            return {
                "symbol": symbol,
                "signal_type": None,
                "message": "No hay señal clara en este momento",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_all_signals(
    interval: str = Query(DEFAULT_TIMEFRAME, description="Intervalo de tiempo"),
    limit: int = Query(100, description="Número de velas para análisis"),
    min_strength: float = Query(60, description="Fuerza mínima de señal", ge=0, le=100)
):
    """
    Obtiene señales de trading para todos los pares
    
    - **interval**: Intervalo de tiempo
    - **min_strength**: Fuerza mínima para incluir señal (0-100)
    """
    try:
        data_dict = {}
        
        for symbol in FOREX_PAIRS:
            try:
                df = data_service.get_candles(symbol, interval, limit)
                data_dict[symbol] = df
            except:
                continue
        
        # Generar señales
        signals = signal_generator.get_all_signals(data_dict)
        
        # Filtrar por fuerza mínima
        filtered = [
            signal_generator.signal_to_dict(s) 
            for s in signals 
            if s.strength >= min_strength
        ]
        
        return {
            "count": len(filtered),
            "interval": interval,
            "min_strength": min_strength,
            "timestamp": datetime.now().isoformat(),
            "signals": filtered
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE SISTEMA ====================

@router.get("/api-usage")
async def get_api_usage():
    """Obtiene uso de la API de TwelveData"""
    try:
        return data_service.get_api_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Verifica que el sistema está funcionando"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "data_service": "ok",
            "indicators": "ok",
            "signal_generator": "ok"
        }
    }
