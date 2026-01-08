"""
Generador de señales de trading
Combina indicadores técnicos para generar señales CALL/PUT
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from dataclasses import dataclass
import sys
sys.path.append('..')
from config import SIGNAL_CONFIG, INDICATORS_CONFIG
from services.indicators_service import TechnicalIndicators, IndicatorResult


@dataclass
class TradingSignal:
    """Representa una señal de trading"""
    symbol: str
    signal_type: str  # CALL o PUT
    strength: float   # 0-100
    price: float
    timestamp: datetime
    indicators: Dict
    confirmations: List[str]
    notes: str


class SignalGenerator:
    """
    Generador de señales basado en indicadores técnicos
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or SIGNAL_CONFIG
        self.indicators = TechnicalIndicators()
        self.min_confirmations = self.config.get("min_confirmations", 2)
        self.min_strength = self.config.get("min_strength", 60)
    
    def analyze_for_signal(self, df: pd.DataFrame, symbol: str) -> Optional[TradingSignal]:
        """
        Analiza datos y genera señal si las condiciones se cumplen
        
        Returns:
            TradingSignal si hay señal válida, None si no
        """
        if len(df) < 50:  # Necesitamos suficientes datos
            return None
        
        # Obtener análisis de todos los indicadores
        analysis = self.indicators.analyze_all(df)
        current_price = df["close"].iloc[-1]
        
        # Contar señales bullish y bearish
        bullish_confirmations = []
        bearish_confirmations = []
        
        # RSI
        rsi = analysis["rsi"]
        if rsi.signal == "OVERSOLD":
            bullish_confirmations.append(f"RSI oversold ({rsi.value})")
        elif rsi.signal == "OVERBOUGHT":
            bearish_confirmations.append(f"RSI overbought ({rsi.value})")
        
        # MACD
        macd = analysis["macd"]
        if macd.signal == "BULLISH":
            bullish_confirmations.append(f"MACD bullish (H: {macd.extra['histogram']})")
            # Bonus si hay cruce
            if macd.extra.get("crossover") == "UP":
                bullish_confirmations.append("MACD crossover UP")
        elif macd.signal == "BEARISH":
            bearish_confirmations.append(f"MACD bearish (H: {macd.extra['histogram']})")
            if macd.extra.get("crossover") == "DOWN":
                bearish_confirmations.append("MACD crossover DOWN")
        
        # Bollinger Bands
        bb = analysis["bollinger"]
        if bb.signal == "BELOW":
            bullish_confirmations.append(f"Price below BB lower ({bb.extra['lower']})")
        elif bb.signal == "ABOVE":
            bearish_confirmations.append(f"Price above BB upper ({bb.extra['upper']})")
        
        # SMA Trend
        sma = analysis["sma"]
        if sma.signal == "BULLISH":
            bullish_confirmations.append("Price above all SMAs")
        elif sma.signal == "BEARISH":
            bearish_confirmations.append("Price below all SMAs")
        
        # EMA Trend
        ema = analysis["ema"]
        if ema.signal == "BULLISH":
            bullish_confirmations.append("Price above all EMAs")
        elif ema.signal == "BEARISH":
            bearish_confirmations.append("Price below all EMAs")
        
        # Determinar tipo de señal y fuerza
        signal_type = None
        confirmations = []
        
        if len(bullish_confirmations) >= self.min_confirmations:
            signal_type = "CALL"
            confirmations = bullish_confirmations
        elif len(bearish_confirmations) >= self.min_confirmations:
            signal_type = "PUT"
            confirmations = bearish_confirmations
        
        if signal_type is None:
            return None
        
        # Calcular fuerza de la señal (0-100)
        strength = self._calculate_strength(
            confirmations, 
            analysis, 
            signal_type
        )
        
        if strength < self.min_strength:
            return None
        
        # Generar notas
        notes = self._generate_notes(signal_type, confirmations, analysis)
        
        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            price=current_price,
            timestamp=datetime.now(),
            indicators={
                "rsi": {"value": rsi.value, "signal": rsi.signal},
                "macd": {"value": macd.value, "signal": macd.signal, "histogram": macd.extra["histogram"]},
                "bollinger": {"position": bb.signal, "percent_b": bb.value},
                "sma": {"trend": sma.signal},
                "ema": {"trend": ema.signal},
            },
            confirmations=confirmations,
            notes=notes
        )
    
    def _calculate_strength(
        self, 
        confirmations: List[str], 
        analysis: Dict[str, IndicatorResult],
        signal_type: str
    ) -> float:
        """
        Calcula la fuerza de la señal (0-100)
        """
        base_strength = 0
        
        # Puntos base por cada confirmación (max 5 indicadores)
        base_strength = min(len(confirmations) * 20, 100)
        
        # Bonus por RSI extremo
        rsi_value = analysis["rsi"].value
        if signal_type == "CALL" and rsi_value < 25:
            base_strength += 10
        elif signal_type == "PUT" and rsi_value > 75:
            base_strength += 10
        
        # Bonus por cruce MACD
        if analysis["macd"].extra.get("crossover"):
            base_strength += 15
        
        # Bonus por tendencia clara en medias móviles
        if analysis["sma"].signal == analysis["ema"].signal:
            if (signal_type == "CALL" and analysis["sma"].signal == "BULLISH") or \
               (signal_type == "PUT" and analysis["sma"].signal == "BEARISH"):
                base_strength += 10
        
        return min(base_strength, 100)
    
    def _generate_notes(
        self, 
        signal_type: str, 
        confirmations: List[str],
        analysis: Dict[str, IndicatorResult]
    ) -> str:
        """
        Genera notas explicativas de la señal
        """
        notes = []
        notes.append(f"Señal {signal_type} generada con {len(confirmations)} confirmaciones:")
        
        for conf in confirmations:
            notes.append(f"  • {conf}")
        
        # Advertencias
        rsi = analysis["rsi"]
        if 40 <= rsi.value <= 60:
            notes.append("⚠️ RSI en zona neutral - señal menos confiable")
        
        bb = analysis["bollinger"]
        if bb.signal == "MIDDLE":
            notes.append("⚠️ Precio en zona media de Bollinger")
        
        return "\n".join(notes)
    
    def get_all_signals(
        self, 
        data_dict: Dict[str, pd.DataFrame]
    ) -> List[TradingSignal]:
        """
        Analiza múltiples símbolos y devuelve todas las señales
        
        Args:
            data_dict: Dict con {symbol: DataFrame}
            
        Returns:
            Lista de señales válidas
        """
        signals = []
        
        for symbol, df in data_dict.items():
            signal = self.analyze_for_signal(df, symbol)
            if signal:
                signals.append(signal)
        
        # Ordenar por fuerza descendente
        signals.sort(key=lambda x: x.strength, reverse=True)
        
        return signals
    
    def signal_to_dict(self, signal: TradingSignal) -> Dict:
        """
        Convierte señal a diccionario para API
        """
        return {
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "strength": signal.strength,
            "price": signal.price,
            "timestamp": signal.timestamp.isoformat(),
            "indicators": signal.indicators,
            "confirmations": signal.confirmations,
            "notes": signal.notes,
        }


# Instancia global
signal_generator = SignalGenerator()


# Funciones de conveniencia
def generate_signal(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """Genera señal para un símbolo"""
    signal = signal_generator.analyze_for_signal(df, symbol)
    if signal:
        return signal_generator.signal_to_dict(signal)
    return None


def get_signals_for_all(data_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
    """Genera señales para múltiples símbolos"""
    signals = signal_generator.get_all_signals(data_dict)
    return [signal_generator.signal_to_dict(s) for s in signals]
