import logging
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from testebin import get_price, get_historical_prices
from binance.client import Client as BinanceClient
from flask_socketio import SocketIO, send, emit
from dotenv import load_dotenv
import os
import threading
import json
import websocket

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
socketio = SocketIO(app, cors_allowed_origins="*")  # Permitir todas as origens

# Suas credenciais do Twilio
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)

# Suas credenciais da Binance
binance_api_key = os.getenv('BINANCE_API_KEY')
binance_api_secret = os.getenv('BINANCE_API_SECRET')
binance_client = BinanceClient(binance_api_key, binance_api_secret)

# Variáveis para armazenar os preços alvo para cada moeda
price_targets = {}

def is_valid_symbol(symbol):
    try:
        binance_client.get_symbol_ticker(symbol=symbol)
        return True
    except Exception:
        return False

@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Responde a uma mensagem recebida com uma resposta interativa."""
    global price_targets

    body = request.values.get('Body', None).strip().lower()
    logging.info(f"Mensagem recebida: {body}")

    response_message = ""

    # Processa a mensagem recebida e toma decisões
    if body.startswith('definir'):
        parts = body.split()
        if len(parts) == 3:
            symbol = parts[1].upper() + 'USDT'
            if is_valid_symbol(symbol):
                try:
                    target_price = float(parts[2])
                    price_targets[symbol] = {'upper': target_price, 'lower': target_price}
                    response_message = f"Alertas de preço definidos para {symbol}: acima de {target_price} e abaixo de {target_price}"
                except ValueError:
                    response_message = f"Formato inválido. Use 'definir [nome_da_moeda] [preço]'. Ex: 'definir sol 180'"
            else:
                response_message = f"Moeda inválida: {parts[1]}"
        else:
            response_message = f"Formato inválido. Use 'definir [nome_da_moeda] [preço]'. Ex: 'definir sol 180'"
    elif body == 'comprar':
        response_message = "Você escolheu comprar!"
    elif body == 'descartar':
        response_message = "Você escolheu descartar!"
    elif body.startswith('historico'):
        parts = body.split()
        if len(parts) == 2:
            symbol = parts[1].upper() + 'USDT'
            if is_valid_symbol(symbol):
                try:
                    historical_prices = get_historical_prices(symbol, '1d', "1 month ago UTC")
                    if historical_prices:
                        response_message = f"Histórico de preços para {parts[1].capitalize()} ({symbol}):\n"
                        response_message += "\n".join([f"{time.date()}: {price}" for time, price in historical_prices[-30:]])  # Últimos 30 dias
                    else:
                        response_message = "Não foi possível obter o histórico de preços. Por favor, tente novamente mais tarde."
                except Exception as e:
                    logging.error(f"Erro ao obter o histórico de preços: {e}")
                    response_message = f"Erro ao obter o histórico de preços: {e}"
            else:
                response_message = f"Moeda inválida: {parts[1]}"
        else:
            response_message = f"Formato inválido. Use 'historico [nome_da_moeda]'. Ex: 'historico bitcoin'"
    else:
        symbol = body.upper() + 'USDT'
        if is_valid_symbol(symbol):
            try:
                # Tenta obter o preço da moeda
                current_price = get_price(symbol)
                response_message = f"O preço atual de {body.capitalize()} ({symbol}) é {current_price:.10f}"
            except Exception as e:
                logging.error(f"Erro ao obter o preço: {e}")
                response_message = f"Erro ao obter o preço da moeda {body.capitalize()}. Por favor, verifique o nome e tente novamente."
        else:
            try:
                # Tenta obter o preço da moeda
                current_price = get_price(body.upper())
                response_message = f"O preço atual de {body.capitalize()}  é {current_price:.10f}"
            except Exception as e:
                logging.error(f"Erro ao obter o preço: {e}")

    logging.info(f"Resposta enviada: {response_message}")
    resp = MessagingResponse()
    resp.message(response_message)

    return str(resp)

@socketio.on('connect')
def handle_connect():
    logging.info('Client connected')
    send('Connected to WebSocket server')

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Client disconnected')

@socketio.on('message')
def handle_message(msg):
    logging.info(f'Mensagem recebida via WebSocket: {msg}')
    send('Mensagem: ' + msg, broadcast=True)

@socketio.on('get_price')
def handle_get_price(data):
    symbol = data.get('symbol', '').upper()
    logging.info(f"Requisição de preço recebida via WebSocket: {data}")

    if not symbol:
        emit('price_response', {'error': 'Símbolo da moeda é necessário'})
        return

    try:
        current_price = get_price(symbol + 'USDT')
        logging.info(f"Preço atual de {symbol}: {current_price}")
        emit('price_response', {'symbol': symbol, 'price': current_price})
    except Exception as e:
        logging.error(f"Erro ao obter o preço: {e}")
        emit('price_response', {'error': str(e)})

# Função para iniciar a conexão WebSocket com a Binance
def start_binance_ws():
    def on_message(ws, message):
        global price_targets

        data_list = json.loads(message)
        for data in data_list:
            symbol = data['s']
            price = float(data['c'])
            print(f"Preço atualizado de {symbol}: {price}")

            if symbol in price_targets:
                targets = price_targets[symbol]
                if targets['upper'] is not None and price >= targets['upper']:
                    send_alert_message(symbol, targets['upper'], "acima")
                    targets['upper'] = None  # Reset the upper target price after alert
                if targets['lower'] is not None and price <= targets['lower']:
                    send_alert_message(symbol, targets['lower'], "abaixo")
                    targets['lower'] = None  # Reset the lower target price after alert

    def send_alert_message(symbol, target_price, condition):
        from_whatsapp_number = 'whatsapp:+14155238886'  # Número do Twilio Sandbox
        to_whatsapp_number = 'whatsapp:+5516997737266'  # Número para enviar a mensagem

        message = twilio_client.messages.create(
            from_=from_whatsapp_number,
            to=to_whatsapp_number,
            body=f"O preço de {symbol} está {condition} do valor alvo de {target_price:.2f}"
        )
        logging.info(f"Mensagem de alerta enviada: {message.sid}")

    def on_error(ws, error):
        logging.error(f"Erro: {error}")

    def on_close(ws):
        logging.info("Conexão WebSocket fechada")

    def on_open(ws):
        logging.info("Conexão WebSocket aberta")
        ws.send(json.dumps({"method": "SUBSCRIBE", "params": ["!ticker@arr"], "id": 1}))

    websocket.enableTrace(False)  # Desativa o traço de WebSocket para evitar logs detalhados
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

if __name__ == "__main__":
    logging.info("Iniciando servidor Flask com SocketIO...")
    ws_thread = threading.Thread(target=start_binance_ws)
    ws_thread.start()
    socketio.run(app, debug=True)
