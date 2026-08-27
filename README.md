# 🚀 Trading Pro - Sistema de Trading en Tiempo Real

Sistema profesional de trading Forex con gráficos en tiempo real estilo IQ Option.

## ✨ Características

- 📊 **Gráficos de Velas Japonesas** - Visualización profesional con Plotly.js
- ⚡ **Datos en Tiempo Real** - Streaming via Finnhub WebSocket
- 📈 **Indicadores Técnicos** - RSI, MACD, Bollinger Bands, SMA, EMA
- 🎯 **Señales de Trading** - Generación automática de señales
- 🎨 **UI Estilo IQ Option** - Interfaz oscura profesional
- 🔄 **Actualización en Vivo** - Precios actualizados al instante

## 🛠️ Tecnologías

- **Backend**: FastAPI + Python
- **Frontend**: HTML5, CSS3, JavaScript
- **Gráficos**: Plotly.js
- **APIs**: TwelveData (histórico), Finnhub (tiempo real)
- **Base de Datos**: SQLite + SQLAlchemy
- **WebSocket**: Comunicación bidireccional en tiempo real

## 📦 Instalación

```bash

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python main.py
```

## 🌐 Uso

1. Abrir http://127.0.0.1:8000 en el navegador
2. Seleccionar un par de divisas (EUR/USD, GBP/USD, etc.)
3. Ver el gráfico en tiempo real con indicadores técnicos

## 📊 Pares Soportados

- EUR/USD
- GBP/USD
- USD/JPY
- AUD/USD
- USD/CAD
- EUR/GBP
- EUR/JPY
- GBP/JPY

## 🔧 Configuración

Editar `config.py` para configurar:
- API Keys (TwelveData, Finnhub)
- Pares de divisas
- Límites de velas
- Puerto del servidor

## 📝 Licencia

MIT License
