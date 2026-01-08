"""
Modelos de base de datos para el sistema de trading
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from database.connection import Base
import enum


def utc_now():
    """Retorna datetime actual en UTC"""
    return datetime.now(timezone.utc)


class SignalType(enum.Enum):
    """Tipo de señal: CALL (compra) o PUT (venta)"""
    CALL = "CALL"
    PUT = "PUT"


class SignalStatus(enum.Enum):
    """Estado de la señal"""
    PENDING = "PENDING"      # Esperando resultado
    WIN = "WIN"              # Señal ganadora
    LOSS = "LOSS"            # Señal perdedora
    EXPIRED = "EXPIRED"      # Expirada sin resultado


class Candle(Base):
    """
    Modelo para almacenar velas/candlesticks
    """
    __tablename__ = "candles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)      # Ej: EUR/USD
    timeframe = Column(String(10), nullable=False, index=True)   # Ej: 1min, 5min
    datetime = Column(DateTime, nullable=False, index=True)      # Timestamp de la vela
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, default=0)
    created_at = Column(DateTime, default=utc_now)
    
    def __repr__(self):
        return f"<Candle {self.symbol} {self.timeframe} {self.datetime}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "datetime": self.datetime.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class Signal(Base):
    """
    Modelo para almacenar señales de trading generadas
    """
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    signal_type = Column(String(10), nullable=False)  # CALL o PUT
    strength = Column(Float, nullable=False)          # Fuerza de la señal (0-100)
    price_at_signal = Column(Float, nullable=False)   # Precio cuando se generó
    
    # Indicadores que confirmaron la señal
    rsi_value = Column(Float)
    macd_value = Column(Float)
    macd_signal = Column(Float)
    bollinger_position = Column(String(20))  # ABOVE, BELOW, MIDDLE
    sma_trend = Column(String(20))           # BULLISH, BEARISH, NEUTRAL
    ema_trend = Column(String(20))           # BULLISH, BEARISH, NEUTRAL
    
    # Resultado
    status = Column(String(20), default="PENDING")
    price_at_expiry = Column(Float)
    profit_loss = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now, index=True)
    expires_at = Column(DateTime)
    closed_at = Column(DateTime)
    
    # Notas/razón de la señal
    notes = Column(Text)
    
    def __repr__(self):
        return f"<Signal {self.symbol} {self.signal_type} {self.strength}%>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "signal_type": self.signal_type,
            "strength": self.strength,
            "price_at_signal": self.price_at_signal,
            "rsi_value": self.rsi_value,
            "macd_value": self.macd_value,
            "bollinger_position": self.bollinger_position,
            "sma_trend": self.sma_trend,
            "ema_trend": self.ema_trend,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "notes": self.notes,
        }


class IndicatorSnapshot(Base):
    """
    Snapshot de indicadores técnicos en un momento dado
    """
    __tablename__ = "indicator_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    datetime = Column(DateTime, nullable=False, index=True)
    
    # Precio actual
    price = Column(Float, nullable=False)
    
    # RSI
    rsi = Column(Float)
    rsi_signal = Column(String(20))  # OVERBOUGHT, OVERSOLD, NEUTRAL
    
    # MACD
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    macd_trend = Column(String(20))  # BULLISH, BEARISH, NEUTRAL
    
    # Bollinger Bands
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    bb_position = Column(String(20))  # ABOVE, BELOW, MIDDLE
    
    # SMAs
    sma_10 = Column(Float)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_trend = Column(String(20))
    
    # EMAs
    ema_9 = Column(Float)
    ema_21 = Column(Float)
    ema_55 = Column(Float)
    ema_trend = Column(String(20))
    
    created_at = Column(DateTime, default=utc_now)
    
    def __repr__(self):
        return f"<IndicatorSnapshot {self.symbol} {self.datetime}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "datetime": self.datetime.isoformat(),
            "price": self.price,
            "rsi": {"value": self.rsi, "signal": self.rsi_signal},
            "macd": {
                "value": self.macd,
                "signal": self.macd_signal,
                "histogram": self.macd_histogram,
                "trend": self.macd_trend
            },
            "bollinger": {
                "upper": self.bb_upper,
                "middle": self.bb_middle,
                "lower": self.bb_lower,
                "position": self.bb_position
            },
            "sma": {
                "sma_10": self.sma_10,
                "sma_20": self.sma_20,
                "sma_50": self.sma_50,
                "trend": self.sma_trend
            },
            "ema": {
                "ema_9": self.ema_9,
                "ema_21": self.ema_21,
                "ema_55": self.ema_55,
                "trend": self.ema_trend
            }
        }


class TradingConfig(Base):
    """
    Configuración personalizada del usuario
    """
    __tablename__ = "trading_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f"<TradingConfig {self.key}={self.value}>"


class TradeHistory(Base):
    """
    Historial de trades (para tracking y análisis)
    """
    __tablename__ = "trade_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    symbol = Column(String(20), nullable=False)
    trade_type = Column(String(10), nullable=False)  # CALL o PUT
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    amount = Column(Float, default=0)  # Monto invertido (si aplica)
    result = Column(String(10))  # WIN, LOSS
    profit_loss_percent = Column(Float)
    
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)
    duration_seconds = Column(Integer)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=utc_now)
    
    def __repr__(self):
        return f"<TradeHistory {self.symbol} {self.trade_type} {self.result}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "trade_type": self.trade_type,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "result": self.result,
            "profit_loss_percent": self.profit_loss_percent,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "duration_seconds": self.duration_seconds,
        }
