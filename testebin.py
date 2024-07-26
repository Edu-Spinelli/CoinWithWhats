from binance.client import Client
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv() # Carrega as variáveis de ambiente do arquivo .env

# Suas chaves da API da Binance
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

client = Client(api_key, api_secret)

def get_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def get_historical_prices(symbol, interval, start_str, end_str=None):
    """Obtém o histórico de preços de uma criptomoeda."""
    try:
        klines = client.get_historical_klines(symbol, interval, start_str, end_str)
        prices = []
        for kline in klines:
            time = datetime.fromtimestamp(kline[0] / 1000)
            close_price = float(kline[4])
            prices.append((time, close_price))
        return prices
    except Exception as e:
        print(f"Erro ao obter o histórico de preços: {e}")
        return []

# Exemplo de uso
if __name__ == "__main__":
    symbol = 'DOGEUSDT'  # Par de moedas
    current_price = get_price(symbol)
    print(f"O preço atual de {symbol} é {current_price}")

    historical_prices = get_historical_prices(symbol, Client.KLINE_INTERVAL_1DAY, "1 month ago UTC")
    print("Histórico de preços (último mês):")
    for time, price in historical_prices:
        print(f"{time}: {price}")
