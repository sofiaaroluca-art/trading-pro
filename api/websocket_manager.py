"""
WebSocket Manager para streaming de datos en tiempo real
Usa Finnhub WebSocket para precios en tiempo real GRATIS
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import asyncio
import json
from datetime import datetime
import sys
sys.path.append('..')
from services.data_service import TwelveDataService
from services.indicators_service import TechnicalIndicators
from services.signal_service import SignalGenerator
from services.realtime_service import FinnhubRealtimeService
from config import FOREX_PAIRS, DEFAULT_TIMEFRAME, FINNHUB_API_KEY


class ConnectionManager:
    """
    Gestiona conexiones WebSocket activas
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}  # WebSocket -> Set of symbols
    
    async def connect(self, websocket: WebSocket):
        """Acepta nueva conexión WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        print(f"✅ Nueva conexión WebSocket. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Desconecta un WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        print(f"❌ Conexión cerrada. Total: {len(self.active_connections)}")
    
    def subscribe(self, websocket: WebSocket, symbols: List[str]):
        """Suscribe un WebSocket a símbolos específicos"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(symbols)
    
    def unsubscribe(self, websocket: WebSocket, symbols: List[str]):
        """Desuscribe un WebSocket de símbolos"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket] -= set(symbols)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Envía mensaje a un WebSocket específico"""
        try:
            await websocket.send_json(message)
        except:
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Envía mensaje a todas las conexiones"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Limpiar desconectados
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_subscribers(self, symbol: str, message: dict):
        """Envía mensaje solo a suscriptores de un símbolo"""
        disconnected = []
        for connection, symbols in self.subscriptions.items():
            if symbol in symbols or not symbols:  # Si no hay suscripción, envía todo
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)


class RealTimeStreamer:
    """
    Streamer de datos en tiempo real usando Finnhub WebSocket
    SINGLETON: Solo una conexión a Finnhub
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls, manager: ConnectionManager):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, manager: ConnectionManager):
        if RealTimeStreamer._initialized:
            return
        RealTimeStreamer._initialized = True
        
        self.manager = manager
        self.data_service = TwelveDataService()
        self.indicators = TechnicalIndicators()
        self.signal_generator = SignalGenerator()
        self.is_running = False
        self.finnhub_connected = False
        self.prices: Dict[str, Dict] = {}
        self._finnhub_task = None
        self._connection_lock = asyncio.Lock()
    
    async def start_realtime(self):
        """Inicia conexión WebSocket con Finnhub para tiempo real"""
        async with self._connection_lock:
            if self.finnhub_connected or self.is_running:
                return
            
            self.is_running = True
            self._finnhub_task = asyncio.create_task(self._finnhub_stream())
            print("🚀 Streaming en tiempo real iniciado (Finnhub)")
    
    async def _finnhub_stream(self):
        """Conecta y escucha Finnhub WebSocket"""
        import websockets
        
        url = f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}"
        
        # Mapeo de símbolos
        symbol_map = {
            "OANDA:EUR_USD": "EUR/USD",
            "OANDA:GBP_USD": "GBP/USD",
            "OANDA:USD_JPY": "USD/JPY",
            "OANDA:AUD_USD": "AUD/USD",
            "OANDA:USD_CAD": "USD/CAD",
            "OANDA:EUR_GBP": "EUR/GBP",
            "OANDA:EUR_JPY": "EUR/JPY",
            "OANDA:GBP_JPY": "GBP/JPY",
        }
        
        reverse_map = {v.replace("/", "_"): v for v in FOREX_PAIRS}
        
        while self.is_running:
            try:
                async with websockets.connect(url, ping_interval=30) as ws:
                    self.finnhub_connected = True
                    print("✅ Conectado a Finnhub WebSocket")
                    
                    # Suscribirse a todos los pares
                    for symbol in FOREX_PAIRS:
                        finnhub_symbol = f"OANDA:{symbol.replace('/', '_')}"
                        await ws.send(json.dumps({"type": "subscribe", "symbol": finnhub_symbol}))
                        print(f"📡 Suscrito a {symbol}")
                    
                    # Escuchar mensajes
                    while self.is_running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60)
                            data = json.loads(message)
                            
                            if data.get("type") == "trade":
                                await self._process_finnhub_trades(data.get("data", []), symbol_map)
                            
                        except asyncio.TimeoutError:
                            # Enviar ping para mantener conexión
                            await ws.send(json.dumps({"type": "ping"}))
                            
            except Exception as e:
                print(f"⚠️ Error Finnhub WebSocket: {e}")
                self.finnhub_connected = False
                await asyncio.sleep(3)
    
    async def _process_finnhub_trades(self, trades: List[Dict], symbol_map: Dict):
        """Procesa trades de Finnhub y envía a clientes"""
        updates = {}
        
        for trade in trades:
            finnhub_symbol = trade.get("s", "")
            price = trade.get("p")
            timestamp = trade.get("t")
            
            # Convertir símbolo
            symbol = symbol_map.get(finnhub_symbol)
            if not symbol:
                # Intentar formato alternativo
                clean = finnhub_symbol.replace("OANDA:", "").replace("_", "/")
                if clean in FOREX_PAIRS:
                    symbol = clean
                else:
                    continue
            
            old_price = self.prices.get(symbol, {}).get("price", price)
            
            self.prices[symbol] = {
                "symbol": symbol,
                "price": price,
                "previous": old_price,
                "change": round(price - old_price, 6) if old_price else 0,
                "timestamp": datetime.now().isoformat(),
                "realtime": True
            }
            
            updates[symbol] = self.prices[symbol]
        
        # Enviar actualizaciones a todos los clientes
        if updates and self.manager.active_connections:
            message = {
                "type": "realtime_prices",
                "timestamp": datetime.now().isoformat(),
                "data": updates
            }
            await self.manager.broadcast(message)
    
    def stop_realtime(self):
        """Detiene el streaming en tiempo real"""
        self.is_running = False
        self.finnhub_connected = False
        if self._finnhub_task:
            self._finnhub_task.cancel()
        print("🛑 Streaming en tiempo real detenido")
    
    async def start_streaming(self):
        """Inicia el streaming de datos en tiempo real"""
        await self.start_realtime()
    
    def stop_streaming(self):
        """Detiene el streaming"""
        self.stop_realtime()
    
    async def send_analysis(self, websocket: WebSocket, symbol: str, interval: str = DEFAULT_TIMEFRAME):
        """Envía análisis técnico a un cliente"""
        try:
            df = self.data_service.get_candles(symbol, interval, 100)
            analysis = self.indicators.get_analysis_summary(df)
            
            message = {
                "type": "analysis",
                "symbol": symbol,
                "interval": interval,
                "timestamp": datetime.now().isoformat(),
                "data": analysis
            }
            
            await self.manager.send_personal_message(message, websocket)
            
        except Exception as e:
            await self.manager.send_personal_message({
                "type": "error",
                "message": str(e)
            }, websocket)
    
    async def send_signal(self, websocket: WebSocket, symbol: str, interval: str = DEFAULT_TIMEFRAME):
        """Envía señal de trading a un cliente"""
        try:
            df = self.data_service.get_candles(symbol, interval, 100)
            signal = self.signal_generator.analyze_for_signal(df, symbol)
            
            if signal:
                message = {
                    "type": "signal",
                    "timestamp": datetime.now().isoformat(),
                    "data": self.signal_generator.signal_to_dict(signal)
                }
            else:
                message = {
                    "type": "signal",
                    "timestamp": datetime.now().isoformat(),
                    "data": None,
                    "message": "No hay señal clara"
                }
            
            await self.manager.send_personal_message(message, websocket)
            
        except Exception as e:
            await self.manager.send_personal_message({
                "type": "error",
                "message": str(e)
            }, websocket)
    
    async def send_all_signals(self, websocket: WebSocket, interval: str = DEFAULT_TIMEFRAME):
        """Envía señales de todos los pares"""
        try:
            data_dict = {}
            for symbol in FOREX_PAIRS:
                try:
                    df = self.data_service.get_candles(symbol, interval, 100)
                    data_dict[symbol] = df
                except:
                    continue
            
            signals = self.signal_generator.get_all_signals(data_dict)
            
            message = {
                "type": "all_signals",
                "timestamp": datetime.now().isoformat(),
                "count": len(signals),
                "data": [self.signal_generator.signal_to_dict(s) for s in signals]
            }
            
            await self.manager.send_personal_message(message, websocket)
            
        except Exception as e:
            await self.manager.send_personal_message({
                "type": "error",
                "message": str(e)
            }, websocket)


# Instancias globales
manager = ConnectionManager()
streamer = RealTimeStreamer(manager)
_realtime_started = False


async def websocket_handler(websocket: WebSocket):
    """
    Handler principal para conexiones WebSocket
    """
    global _realtime_started
    
    await manager.connect(websocket)
    
    # Iniciar streaming en tiempo real solo UNA VEZ
    if not _realtime_started and not streamer.finnhub_connected:
        _realtime_started = True
        asyncio.create_task(streamer.start_realtime())
    
    try:
        while True:
            # Recibir mensajes del cliente
            data = await websocket.receive_json()
            
            action = data.get("action")
            symbol = data.get("symbol")
            interval = data.get("interval", DEFAULT_TIMEFRAME)
            
            if action == "subscribe":
                symbols = data.get("symbols", FOREX_PAIRS)
                manager.subscribe(websocket, symbols)
                await manager.send_personal_message({
                    "type": "subscribed",
                    "symbols": list(manager.subscriptions[websocket]),
                    "realtime": streamer.finnhub_connected,
                    "source": "finnhub"
                }, websocket)
            
            elif action == "unsubscribe":
                symbols = data.get("symbols", [])
                manager.unsubscribe(websocket, symbols)
                await manager.send_personal_message({
                    "type": "unsubscribed",
                    "symbols": symbols
                }, websocket)
            
            elif action == "start_realtime":
                # Ya iniciado globalmente
                await manager.send_personal_message({
                    "type": "realtime_started",
                    "message": "Streaming en tiempo real activo",
                    "connected": streamer.finnhub_connected
                }, websocket)
            
            elif action == "get_analysis":
                if symbol:
                    await streamer.send_analysis(websocket, symbol, interval)
            
            elif action == "get_signal":
                if symbol:
                    await streamer.send_signal(websocket, symbol, interval)
            
            elif action == "get_all_signals":
                await streamer.send_all_signals(websocket, interval)
            
            elif action == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "realtime_connected": streamer.finnhub_connected
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    
    except Exception as e:
        print(f"Error en WebSocket: {e}")
        manager.disconnect(websocket)
