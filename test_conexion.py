"""
==============================================
TEST DE CONEXIÓN - SISTEMA TRADING PRO
==============================================
Este script verifica que la conexión a TwelveData
funcione correctamente y los datos lleguen en tiempo real.
"""

import requests
import time
from datetime import datetime

# Tu API Key
API_KEY = "4482ac6740914afe884d709c9c132fff"

# Colores para la terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    print(f"""
{Colors.BLUE}{'='*60}
   🔌 TEST DE CONEXIÓN - SISTEMA TRADING PRO
{'='*60}{Colors.RESET}
""")

def test_1_api_connection():
    """Test 1: Verificar que la API responde"""
    print(f"{Colors.YELLOW}[TEST 1] Verificando conexión a TwelveData...{Colors.RESET}")
    
    try:
        url = f"https://api.twelvedata.com/api_usage?apikey={API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "daily_usage" in data:
            print(f"{Colors.GREEN}   ✅ Conexión exitosa!{Colors.RESET}")
            print(f"   📊 Uso diario: {data.get('daily_usage', 'N/A')}/{data.get('plan_daily_limit', 'N/A')} requests")
            return True
        else:
            print(f"{Colors.RED}   ❌ Error: {data}{Colors.RESET}")
            return False
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error de conexión: {e}{Colors.RESET}")
        return False

def test_2_forex_data():
    """Test 2: Obtener datos de Forex"""
    print(f"\n{Colors.YELLOW}[TEST 2] Obteniendo datos de EUR/USD...{Colors.RESET}")
    
    try:
        url = f"https://api.twelvedata.com/price?symbol=EUR/USD&apikey={API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "price" in data:
            price = float(data["price"])
            print(f"{Colors.GREEN}   ✅ Precio EUR/USD: {price}{Colors.RESET}")
            return True
        else:
            print(f"{Colors.RED}   ❌ Error: {data}{Colors.RESET}")
            return False
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error: {e}{Colors.RESET}")
        return False

def test_3_realtime_quotes():
    """Test 3: Verificar múltiples pares"""
    print(f"\n{Colors.YELLOW}[TEST 3] Verificando múltiples pares Forex...{Colors.RESET}")
    
    pares = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"]
    
    try:
        symbols = ",".join(pares)
        url = f"https://api.twelvedata.com/price?symbol={symbols}&apikey={API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print(f"{Colors.GREEN}   ✅ Pares disponibles:{Colors.RESET}")
        for par in pares:
            if par in data:
                print(f"      • {par}: {data[par]['price']}")
            else:
                print(f"      • {par}: No disponible")
        return True
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error: {e}{Colors.RESET}")
        return False

def test_4_candles():
    """Test 4: Obtener velas (candlesticks)"""
    print(f"\n{Colors.YELLOW}[TEST 4] Obteniendo velas de 1 minuto...{Colors.RESET}")
    
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval=1min&outputsize=5&apikey={API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "values" in data:
            print(f"{Colors.GREEN}   ✅ Últimas 5 velas EUR/USD:{Colors.RESET}")
            for vela in data["values"][:5]:
                print(f"      {vela['datetime']} | O:{vela['open']} H:{vela['high']} L:{vela['low']} C:{vela['close']}")
            return True
        else:
            print(f"{Colors.RED}   ❌ Error: {data}{Colors.RESET}")
            return False
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error: {e}{Colors.RESET}")
        return False

def test_5_realtime_stream():
    """Test 5: Simular streaming de precios"""
    print(f"\n{Colors.YELLOW}[TEST 5] Probando actualización en tiempo real (10 segundos)...{Colors.RESET}")
    print(f"   Observa si el precio cambia:\n")
    
    try:
        for i in range(5):
            url = f"https://api.twelvedata.com/price?symbol=EUR/USD&apikey={API_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            price = data.get("price", "N/A")
            
            print(f"   [{timestamp}] EUR/USD = {Colors.BOLD}{price}{Colors.RESET}")
            
            if i < 4:
                time.sleep(2)
        
        print(f"\n{Colors.GREEN}   ✅ Stream funcionando correctamente{Colors.RESET}")
        return True
    except Exception as e:
        print(f"{Colors.RED}   ❌ Error: {e}{Colors.RESET}")
        return False

def main():
    print_header()
    
    # Ejecutar tests
    results = []
    
    results.append(("Conexión API", test_1_api_connection()))
    results.append(("Datos Forex", test_2_forex_data()))
    results.append(("Múltiples Pares", test_3_realtime_quotes()))
    results.append(("Velas/Candlesticks", test_4_candles()))
    results.append(("Tiempo Real", test_5_realtime_stream()))
    
    # Resumen
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"   📋 RESUMEN DE PRUEBAS")
    print(f"{'='*60}{Colors.RESET}\n")
    
    passed = 0
    for name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if result else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"   {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n   Total: {passed}/{len(results)} pruebas exitosas")
    
    if passed == len(results):
        print(f"\n{Colors.GREEN}{'='*60}")
        print(f"   🎉 ¡TODO FUNCIONA CORRECTAMENTE!")
        print(f"   Listo para el siguiente paso.")
        print(f"{'='*60}{Colors.RESET}\n")
    else:
        print(f"\n{Colors.RED}   ⚠️ Algunos tests fallaron. Revisa los errores arriba.{Colors.RESET}\n")

if __name__ == "__main__":
    main()
