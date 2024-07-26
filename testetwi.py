from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from testebin import get_price, get_historical_prices
from dotenv import load_dotenv
import os

load_dotenv() # Carrega as variáveis de ambiente do arquivo .env
app = Flask(__name__)

# Suas credenciais do Twilio
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_client = Client(account_sid, auth_token)

# Mapeamento das principais criptomoedas para seus símbolos na Binance
crypto_mapping = {
    'bitcoin': 'BTCUSDT',
    'ethereum': 'ETHUSDT',
    'binance coin': 'BNBUSDT',
    'ripple': 'XRPUSDT',
    'cardano': 'ADAUSDT',
    'solana': 'SOLUSDT',
    'dogecoin': 'DOGEUSDT',
    'polkadot': 'DOTUSDT',
    'litecoin': 'LTCUSDT',
    'chainlink': 'LINKUSDT'
}

@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Responde a uma mensagem recebida com uma resposta interativa."""
    body = request.values.get('Body', None).strip().lower()

    response_message = ""

    # Processa a mensagem recebida e toma decisões
    if body == 'comprar':
        response_message = "Você escolheu comprar!"
    elif body == 'descartar':
        response_message = "Você escolheu descartar!"
    elif body.startswith('historico'):
        parts = body.split()
        if len(parts) == 2 and parts[1] in crypto_mapping:
            symbol = crypto_mapping[parts[1]]
            try:
                historical_prices = get_historical_prices(symbol, '1d', "1 month ago UTC")
                if historical_prices:
                    response_message = f"Histórico de preços para {parts[1].capitalize()} ({symbol}):\n"
                    response_message += "\n".join([f"{time.date()}: {price}" for time, price in historical_prices[-7:]])  # Últimos 7 dias
                else:
                    response_message = "Não foi possível obter o histórico de preços. Por favor, tente novamente mais tarde."
            except Exception as e:
                response_message = f"Erro ao obter o histórico de preços: {e}"
        else:
            response_message = "Formato inválido. Use 'historico [nome_da_moeda]'. Ex: 'historico bitcoin'"
    else:
        if body in crypto_mapping:
            symbol = crypto_mapping[body]
            try:
                # Tenta obter o preço da moeda
                current_price = get_price(symbol)
                response_message = f"O preço atual de {body.capitalize()} ({symbol}) é {current_price:.2f}"
            except Exception as e:
                response_message = "Erro ao obter o preço. Por favor, tente novamente mais tarde."
        else:
            try:
                current_price = get_price(body.capitalize())
                response_message = f"O preço atual de {body.capitalize()} ({symbol}) é {current_price:.2f}"

            except Exception as e:
                response_message = f"Moeda não reconhecida. Por favor, envie 'comprar', 'descartar' ou o nome {body} de uma criptomoeda válida (ex: bitcoin, ethereum)."

    resp = MessagingResponse()
    resp.message(response_message)

    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)
