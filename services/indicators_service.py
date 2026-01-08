"""
Servicio de indicadores técnicos
Calcula RSI, MACD, Bollinger Bands, SMA, EMA
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import sys
sys.path.append('..')
from config import INDICATORS_CONFIG


@dataclass
class IndicatorResult:
    """Resultado de un indicador con valor y señal"""
    value: float
    signal: str  # BULLISH, BEARISH, NEUTRAL, OVERBOUGHT, OVERSOLD
    extra: Dict = None


class TechnicalIndicators:
    """
    Calculador de indicadores técnicos
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or INDICATORS_CONFIG
    
    # ==================== RSI ====================
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Calcula el Relative Strength Index (RSI)
        
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        period = period or self.config["rsi"]["period"]
        
        delta = df["close"].diff()
        
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_rsi_signal(self, rsi_value: float) -> str:
        """
        Interpreta el valor RSI
        """
        overbought = self.config["rsi"]["overbought"]
        oversold = self.config["rsi"]["oversold"]
        
        if rsi_value >= overbought:
            return "OVERBOUGHT"  # Posible señal PUT
        elif rsi_value <= oversold:
            return "OVERSOLD"   # Posible señal CALL
        else:
            return "NEUTRAL"
    
    def analyze_rsi(self, df: pd.DataFrame) -> IndicatorResult:
        """Calcula RSI y devuelve resultado con interpretación"""
        rsi = self.calculate_rsi(df)
        current_rsi = rsi.iloc[-1]
        
        return IndicatorResult(
            value=round(current_rsi, 2),
            signal=self.get_rsi_signal(current_rsi),
            extra={"previous": round(rsi.iloc[-2], 2) if len(rsi) > 1 else None}
        )
    
    # ==================== MACD ====================
    
    def calculate_macd(
        self, 
        df: pd.DataFrame,
        fast_period: int = None,
        slow_period: int = None,
        signal_period: int = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calcula MACD (Moving Average Convergence Divergence)
        
        MACD = EMA(12) - EMA(26)
        Signal = EMA(9) del MACD
        Histogram = MACD - Signal
        """
        fast = fast_period or self.config["macd"]["fast_period"]
        slow = slow_period or self.config["macd"]["slow_period"]
        signal = signal_period or self.config["macd"]["signal_period"]
        
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def get_macd_signal(self, macd: float, signal: float, histogram: float) -> str:
        """
        Interpreta MACD
        """
        # Cruce de líneas
        if macd > signal and histogram > 0:
            return "BULLISH"  # Señal CALL
        elif macd < signal and histogram < 0:
            return "BEARISH"  # Señal PUT
        else:
            return "NEUTRAL"
    
    def analyze_macd(self, df: pd.DataFrame) -> IndicatorResult:
        """Calcula MACD y devuelve resultado con interpretación"""
        macd_line, signal_line, histogram = self.calculate_macd(df)
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        
        return IndicatorResult(
            value=round(current_macd, 6),
            signal=self.get_macd_signal(current_macd, current_signal, current_histogram),
            extra={
                "signal_line": round(current_signal, 6),
                "histogram": round(current_histogram, 6),
                "crossover": "UP" if current_histogram > 0 and histogram.iloc[-2] <= 0 else 
                            "DOWN" if current_histogram < 0 and histogram.iloc[-2] >= 0 else None
            }
        )
    
    # ==================== BOLLINGER BANDS ====================
    
    def calculate_bollinger_bands(
        self, 
        df: pd.DataFrame,
        period: int = None,
        std_dev: float = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calcula Bandas de Bollinger
        
        Middle = SMA(20)
        Upper = Middle + (2 * STD)
        Lower = Middle - (2 * STD)
        """
        period = period or self.config["bollinger"]["period"]
        std = std_dev or self.config["bollinger"]["std_dev"]
        
        middle = df["close"].rolling(window=period).mean()
        std_dev = df["close"].rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def get_bollinger_signal(self, price: float, upper: float, middle: float, lower: float) -> str:
        """
        Interpreta posición del precio respecto a Bollinger
        """
        if price >= upper:
            return "ABOVE"  # Posible señal PUT (sobrecompra)
        elif price <= lower:
            return "BELOW"  # Posible señal CALL (sobreventa)
        else:
            return "MIDDLE"
    
    def analyze_bollinger(self, df: pd.DataFrame) -> IndicatorResult:
        """Calcula Bollinger Bands y devuelve resultado"""
        upper, middle, lower = self.calculate_bollinger_bands(df)
        
        current_price = df["close"].iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]
        
        # Calcular %B (posición del precio entre las bandas)
        percent_b = (current_price - current_lower) / (current_upper - current_lower) if (current_upper - current_lower) != 0 else 0.5
        
        return IndicatorResult(
            value=round(percent_b, 4),
            signal=self.get_bollinger_signal(current_price, current_upper, current_middle, current_lower),
            extra={
                "upper": round(current_upper, 5),
                "middle": round(current_middle, 5),
                "lower": round(current_lower, 5),
                "bandwidth": round((current_upper - current_lower) / current_middle * 100, 2)
            }
        )
    
    # ==================== SMA ====================
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calcula Simple Moving Average"""
        return df["close"].rolling(window=period).mean()
    
    def analyze_sma(self, df: pd.DataFrame) -> IndicatorResult:
        """Calcula múltiples SMAs y analiza tendencia"""
        periods = self.config["sma"]["periods"]
        smas = {}
        
        for period in periods:
            smas[f"sma_{period}"] = self.calculate_sma(df, period).iloc[-1]
        
        current_price = df["close"].iloc[-1]
        
        # Determinar tendencia
        sma_values = list(smas.values())
        above_count = sum(1 for sma in sma_values if current_price > sma)
        
        if above_count == len(sma_values):
            trend = "BULLISH"
        elif above_count == 0:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return IndicatorResult(
            value=round(sma_values[0], 5),  # SMA más corto
            signal=trend,
            extra={k: round(v, 5) for k, v in smas.items()}
        )
    
    # ==================== EMA ====================
    
    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calcula Exponential Moving Average"""
        return df["close"].ewm(span=period, adjust=False).mean()
    
    def analyze_ema(self, df: pd.DataFrame) -> IndicatorResult:
        """Calcula múltiples EMAs y analiza tendencia"""
        periods = self.config["ema"]["periods"]
        emas = {}
        
        for period in periods:
            emas[f"ema_{period}"] = self.calculate_ema(df, period).iloc[-1]
        
        current_price = df["close"].iloc[-1]
        
        # Determinar tendencia basada en EMAs
        ema_values = list(emas.values())
        above_count = sum(1 for ema in ema_values if current_price > ema)
        
        # También verificar si EMAs están alineadas
        sorted_emas = sorted(ema_values, reverse=True)
        aligned_bullish = ema_values == sorted_emas[::-1]  # Menor a mayor = bullish
        aligned_bearish = ema_values == sorted_emas  # Mayor a menor = bearish
        
        if above_count == len(ema_values) or aligned_bullish:
            trend = "BULLISH"
        elif above_count == 0 or aligned_bearish:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return IndicatorResult(
            value=round(ema_values[0], 5),
            signal=trend,
            extra={k: round(v, 5) for k, v in emas.items()}
        )
    
    # ==================== ANÁLISIS COMPLETO ====================
    
    def analyze_all(self, df: pd.DataFrame) -> Dict[str, IndicatorResult]:
        """
        Ejecuta todos los indicadores y devuelve análisis completo
        """
        return {
            "rsi": self.analyze_rsi(df),
            "macd": self.analyze_macd(df),
            "bollinger": self.analyze_bollinger(df),
            "sma": self.analyze_sma(df),
            "ema": self.analyze_ema(df),
        }
    
    def get_analysis_summary(self, df: pd.DataFrame) -> Dict:
        """
        Resumen del análisis para mostrar en UI
        """
        analysis = self.analyze_all(df)
        current_price = df["close"].iloc[-1]
        
        bullish_count = 0
        bearish_count = 0
        
        for name, result in analysis.items():
            if result.signal in ["BULLISH", "OVERSOLD", "BELOW"]:
                bullish_count += 1
            elif result.signal in ["BEARISH", "OVERBOUGHT", "ABOVE"]:
                bearish_count += 1
        
        return {
            "price": round(current_price, 5),
            "timestamp": df["datetime"].iloc[-1].isoformat() if "datetime" in df.columns else None,
            "indicators": {
                name: {
                    "value": result.value,
                    "signal": result.signal,
                    "extra": result.extra
                } for name, result in analysis.items()
            },
            "summary": {
                "bullish_signals": bullish_count,
                "bearish_signals": bearish_count,
                "neutral_signals": len(analysis) - bullish_count - bearish_count,
                "overall_bias": "BULLISH" if bullish_count > bearish_count else 
                               "BEARISH" if bearish_count > bullish_count else "NEUTRAL"
            }
        }


# Instancia global
indicators = TechnicalIndicators()


# Funciones de conveniencia
def analyze_symbol(df: pd.DataFrame) -> Dict:
    """Analiza un símbolo con todos los indicadores"""
    return indicators.get_analysis_summary(df)
