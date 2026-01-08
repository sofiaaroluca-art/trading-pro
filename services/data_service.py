"""
Servicio para obtener datos de TwelveData API
Maneja tanto datos históricos como tiempo real
CON CACHÉ para evitar exceder límites de API
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import sys
sys.path.append('..')
from config import TWELVEDATA_API_KEY, FOREX_PAIRS, CANDLES_LIMIT


class DataCache:
    """Caché simple para datos de la API"""
    
    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Dict] = {}
    
    def get(self, key: str) -> Optional[Dict]:
        """Obtiene valor del caché si no ha expirado"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() - entry["timestamp"] < timedelta(seconds=self.ttl):
                return entry["data"]
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, data):
        """Guarda valor en caché"""
        self._cache[key] = {
            "data": data,
            "timestamp": datetime.now()
        }
    
    def clear(self):
        """Limpia el caché"""
        self._cache.clear()


class TwelveDataService:
    """
    Cliente para la API de TwelveData con caché integrado
    """
    
    BASE_URL = "https://api.twelvedata.com"
    
    # Rate limiting: 8 requests por minuto en plan gratuito
    RATE_LIMIT = 8
    RATE_WINDOW = 60  # segundos
    
    def __init__(self, api_key: str = TWELVEDATA_API_KEY):
        self.api_key = api_key
        self.session = requests.Session()
        self._request_count = 0
        self._last_request_time = None
        self._request_times: List[datetime] = []
        
        # Caché para diferentes tipos de datos
        self.price_cache = DataCache(ttl_seconds=15)  # Precios: 15 seg
        self.candles_cache = DataCache(ttl_seconds=60)  # Velas: 60 seg
        self.quote_cache = DataCache(ttl_seconds=30)  # Quotes: 30 seg
    
    def _check_rate_limit(self):
        """Verifica y espera si es necesario para no exceder rate limit"""
        now = datetime.now()
        
        # Limpiar requests antiguos
        self._request_times = [
            t for t in self._request_times 
            if now - t < timedelta(seconds=self.RATE_WINDOW)
        ]
        
        # Si estamos en el límite, esperar
        if len(self._request_times) >= self.RATE_LIMIT:
            oldest = min(self._request_times)
            wait_time = (oldest + timedelta(seconds=self.RATE_WINDOW) - now).total_seconds()
            if wait_time > 0:
                print(f"⏳ Rate limit alcanzado, esperando {wait_time:.1f}s...")
                time.sleep(wait_time + 1)
                self._request_times.clear()
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Realiza una petición a la API con manejo de errores y rate limiting
        """
        self._check_rate_limit()
        
        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Verificar errores de la API
            if "status" in data and data["status"] == "error":
                raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
            
            self._request_count += 1
            self._last_request_time = datetime.now()
            self._request_times.append(datetime.now())
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def get_price(self, symbol: str) -> Dict:
        """
        Obtiene el precio actual de un par de divisas (con caché)
        
        Args:
            symbol: Par de divisas (ej: "EUR/USD")
            
        Returns:
            Dict con precio y timestamp
        """
        # Verificar caché primero
        cache_key = f"price_{symbol}"
        cached = self.price_cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("price", {"symbol": symbol})
        
        result = {
            "symbol": symbol,
            "price": float(data["price"]),
            "timestamp": datetime.now().isoformat()
        }
        
        self.price_cache.set(cache_key, result)
        return result
    
    def get_quote(self, symbol: str) -> Dict:
        """
        Obtiene cotización completa con más detalles (con caché)
        """
        # Verificar caché primero
        cache_key = f"quote_{symbol}"
        cached = self.quote_cache.get(cache_key)
        if cached:
            return cached
        
        data = self._make_request("quote", {"symbol": symbol})
        
        result = {
            "symbol": data.get("symbol", symbol),
            "name": data.get("name", ""),
            "open": float(data.get("open", 0)),
            "high": float(data.get("high", 0)),
            "low": float(data.get("low", 0)),
            "close": float(data.get("close", 0)),
            "previous_close": float(data.get("previous_close", 0)),
            "change": float(data.get("change", 0)),
            "percent_change": float(data.get("percent_change", 0)),
            "timestamp": data.get("timestamp", datetime.now().isoformat())
        }
        
        self.quote_cache.set(cache_key, result)
        return result
    
    def get_candles(
        self, 
        symbol: str, 
        interval: str = "1min",
        outputsize: int = CANDLES_LIMIT,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Obtiene velas históricas (con caché)
        
        Args:
            symbol: Par de divisas
            interval: Intervalo de tiempo (1min, 5min, 15min, 30min, 1h, 4h, 1day)
            outputsize: Número de velas a obtener
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)
            
        Returns:
            DataFrame con columnas: datetime, open, high, low, close, volume
        """
        # Verificar caché primero
        cache_key = f"candles_{symbol}_{interval}_{outputsize}"
        cached = self.candles_cache.get(cache_key)
        if cached is not None:
            return cached
        
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = self._make_request("time_series", params)
        
        if "values" not in data:
            raise Exception("No se encontraron datos de velas")
        
        # Convertir a DataFrame
        df = pd.DataFrame(data["values"])
        
        # Convertir tipos
        df["datetime"] = pd.to_datetime(df["datetime"])
        df["open"] = pd.to_numeric(df["open"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        df["close"] = pd.to_numeric(df["close"])
        
        # Ordenar por fecha ascendente
        df = df.sort_values("datetime").reset_index(drop=True)
        
        # Añadir símbolo e intervalo
        df["symbol"] = symbol
        df["interval"] = interval
        
        # Guardar en caché
        self.candles_cache.set(cache_key, df)
        
        return df
    
    def get_multiple_prices(self, symbols: List[str] = None) -> Dict[str, Dict]:
        """
        Obtiene precios de múltiples pares
        
        Args:
            symbols: Lista de pares (usa FOREX_PAIRS por defecto)
            
        Returns:
            Dict con precios por símbolo
        """
        if symbols is None:
            symbols = FOREX_PAIRS
        
        # TwelveData permite consultar múltiples símbolos separados por coma
        symbols_str = ",".join(symbols)
        data = self._make_request("price", {"symbol": symbols_str})
        
        result = {}
        
        # Si es un solo símbolo, viene diferente
        if isinstance(data, dict) and "price" in data:
            result[symbols[0]] = {
                "price": float(data["price"]),
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Múltiples símbolos
            for symbol in symbols:
                if symbol in data and "price" in data[symbol]:
                    result[symbol] = {
                        "price": float(data[symbol]["price"]),
                        "timestamp": datetime.now().isoformat()
                    }
        
        return result
    
    def get_api_usage(self) -> Dict:
        """
        Obtiene el uso de la API
        """
        data = self._make_request("api_usage", {})
        
        return {
            "daily_limit": data.get("daily_usage", 0),
            "daily_limit_max": 800,  # Free tier
            "remaining": 800 - data.get("daily_usage", 0),
            "timestamp": datetime.now().isoformat()
        }
    
    def stream_prices(self, symbols: List[str], callback, interval_seconds: int = 2, duration_seconds: int = 60):
        """
        Simula streaming de precios haciendo polling
        (TwelveData WebSocket requiere plan de pago)
        
        Args:
            symbols: Lista de pares a monitorear
            callback: Función a llamar con cada actualización
            interval_seconds: Segundos entre actualizaciones
            duration_seconds: Duración total del streaming
        """
        start_time = time.time()
        
        while (time.time() - start_time) < duration_seconds:
            try:
                prices = self.get_multiple_prices(symbols)
                callback(prices)
                time.sleep(interval_seconds)
            except Exception as e:
                print(f"Error en streaming: {e}")
                time.sleep(interval_seconds)
    
    @property
    def request_count(self) -> int:
        """Número de requests realizados en esta sesión"""
        return self._request_count


# Instancia global del servicio
data_service = TwelveDataService()


# Funciones de conveniencia
def get_current_price(symbol: str) -> float:
    """Obtiene precio actual de un par"""
    return data_service.get_price(symbol)["price"]


def get_candles(symbol: str, interval: str = "1min", limit: int = 100) -> pd.DataFrame:
    """Obtiene velas históricas"""
    return data_service.get_candles(symbol, interval, limit)


def get_all_prices() -> Dict[str, float]:
    """Obtiene precios de todos los pares configurados"""
    prices = data_service.get_multiple_prices()
    return {symbol: data["price"] for symbol, data in prices.items()}
