"""
Servicio de datos en tiempo real usando Finnhub WebSocket
Finnhub ofrece WebSocket gratuito para Forex
"""
import asyncio
import json
import websockets
from typing import Dict, List, Callable, Optional
from datetime import datetime
import threading
import time


class FinnhubRealtimeService:
    """
    Cliente WebSocket para Finnhub - Datos Forex en tiempo real GRATIS
    
    Documentación: https://finnhub.io/docs/api/websocket-trades
    """
    
    # API Key gratuita de Finnhub (obtener en https://finnhub.io)
    # El plan gratuito incluye WebSocket para Forex
    FINNHUB_API_KEY = "ct25mlhr01qhb16og7tgct25mlhr01qhb16og7u0"  # Demo key - reemplazar con tu key
    WEBSOCKET_URL = f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}"
    
    # Mapeo de símbolos TwelveData -> Finnhub (OANDA format)
    SYMBOL_MAP = {
        "EUR/USD": "OANDA:EUR_USD",
        "GBP/USD": "OANDA:GBP_USD", 
        "USD/JPY": "OANDA:USD_JPY",
        "AUD/USD": "OANDA:AUD_USD",
        "USD/CAD": "OANDA:USD_CAD",
        "EUR/GBP": "OANDA:EUR_GBP",
        "EUR/JPY": "OANDA:EUR_JPY",
        "GBP/JPY": "OANDA:GBP_JPY",
        "NZD/USD": "OANDA:NZD_USD",
        "USD/CHF": "OANDA:USD_CHF",
    }
    
    # Mapeo inverso
    REVERSE_MAP = {v: k for k, v in SYMBOL_MAP.items()}
    
    def __init__(self):
        self.websocket = None
        self.is_connected = False
        self.is_running = False
        self.prices: Dict[str, Dict] = {}
        self.callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._last_update: Dict[str, datetime] = {}
    
    def add_callback(self, callback: Callable):
        """Añade callback para recibir actualizaciones de precios"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Elimina un callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _notify_callbacks(self, data: Dict):
        """Notifica a todos los callbacks"""
        for callback in self.callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"Error en callback: {e}")
    
    async def connect(self):
        """Conecta al WebSocket de Finnhub"""
        try:
            self.websocket = await websockets.connect(
                self.WEBSOCKET_URL,
                ping_interval=30,
                ping_timeout=10
            )
            self.is_connected = True
            print("✅ Conectado a Finnhub WebSocket (Tiempo Real)")
            return True
        except Exception as e:
            print(f"❌ Error conectando a Finnhub: {e}")
            self.is_connected = False
            return False
    
    async def subscribe(self, symbols: List[str] = None):
        """
        Suscribe a símbolos de Forex
        
        Args:
            symbols: Lista de símbolos (formato TwelveData: EUR/USD)
        """
        if not self.websocket or not self.is_connected:
            await self.connect()
        
        if symbols is None:
            symbols = list(self.SYMBOL_MAP.keys())
        
        for symbol in symbols:
            finnhub_symbol = self.SYMBOL_MAP.get(symbol)
            if finnhub_symbol:
                message = {"type": "subscribe", "symbol": finnhub_symbol}
                await self.websocket.send(json.dumps(message))
                print(f"📡 Suscrito a {symbol} ({finnhub_symbol})")
    
    async def unsubscribe(self, symbols: List[str]):
        """Desuscribe de símbolos"""
        if not self.websocket:
            return
        
        for symbol in symbols:
            finnhub_symbol = self.SYMBOL_MAP.get(symbol)
            if finnhub_symbol:
                message = {"type": "unsubscribe", "symbol": finnhub_symbol}
                await self.websocket.send(json.dumps(message))
    
    async def listen(self):
        """Escucha mensajes del WebSocket"""
        self.is_running = True
        
        while self.is_running:
            try:
                if not self.is_connected:
                    await self.connect()
                    await self.subscribe()
                
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "trade":
                    await self._process_trades(data.get("data", []))
                elif data.get("type") == "ping":
                    # Keep-alive
                    pass
                    
            except websockets.ConnectionClosed:
                print("⚠️ Conexión WebSocket cerrada, reconectando...")
                self.is_connected = False
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error en WebSocket: {e}")
                await asyncio.sleep(5)
    
    async def _process_trades(self, trades: List[Dict]):
        """Procesa trades recibidos"""
        for trade in trades:
            finnhub_symbol = trade.get("s")
            price = trade.get("p")
            timestamp = trade.get("t")
            volume = trade.get("v", 0)
            
            # Convertir a formato TwelveData
            symbol = self.REVERSE_MAP.get(finnhub_symbol)
            if not symbol:
                continue
            
            with self._lock:
                old_price = self.prices.get(symbol, {}).get("price", price)
                
                self.prices[symbol] = {
                    "symbol": symbol,
                    "price": price,
                    "previous_price": old_price,
                    "change": price - old_price,
                    "change_percent": ((price - old_price) / old_price * 100) if old_price else 0,
                    "volume": volume,
                    "timestamp": datetime.fromtimestamp(timestamp / 1000).isoformat() if timestamp else datetime.now().isoformat(),
                    "source": "finnhub_realtime"
                }
                self._last_update[symbol] = datetime.now()
            
            # Notificar callbacks
            self._notify_callbacks({
                "type": "price_update",
                "symbol": symbol,
                "data": self.prices[symbol]
            })
    
    def get_price(self, symbol: str) -> Optional[Dict]:
        """Obtiene el último precio de un símbolo"""
        with self._lock:
            return self.prices.get(symbol)
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """Obtiene todos los precios actuales"""
        with self._lock:
            return dict(self.prices)
    
    async def disconnect(self):
        """Desconecta del WebSocket"""
        self.is_running = False
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
            print("🔌 Desconectado de Finnhub WebSocket")


class RealtimePriceManager:
    """
    Gestor de precios en tiempo real
    Combina múltiples fuentes de datos
    """
    
    def __init__(self):
        self.finnhub = FinnhubRealtimeService()
        self.prices: Dict[str, Dict] = {}
        self._running = False
        self._task = None
    
    async def start(self):
        """Inicia el servicio de tiempo real"""
        if self._running:
            return
        
        self._running = True
        
        # Callback para actualizar precios locales
        def update_prices(data):
            if data.get("type") == "price_update":
                symbol = data.get("symbol")
                self.prices[symbol] = data.get("data")
        
        self.finnhub.add_callback(update_prices)
        
        # Iniciar listener
        self._task = asyncio.create_task(self.finnhub.listen())
        print("🚀 Servicio de tiempo real iniciado")
    
    async def stop(self):
        """Detiene el servicio"""
        self._running = False
        await self.finnhub.disconnect()
        if self._task:
            self._task.cancel()
        print("🛑 Servicio de tiempo real detenido")
    
    def get_prices(self) -> Dict[str, Dict]:
        """Obtiene todos los precios actuales"""
        return self.finnhub.get_all_prices()
    
    def add_price_callback(self, callback: Callable):
        """Añade callback para actualizaciones de precio"""
        self.finnhub.add_callback(callback)


# Instancia global
realtime_manager = RealtimePriceManager()
