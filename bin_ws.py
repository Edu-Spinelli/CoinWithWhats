import websocket
import json
import threading

def on_message(ws, message):
    data = json.loads(message)
    symbol = data['s']
    if symbol == "SOLUSDT":
        price = data['c']
        print(f"Preço atualizado de {symbol}: {price}")

def on_error(ws, error):
    print(f"Erro: {error}")

def on_close(ws):
    print("Conexão WebSocket fechada")

def on_open(ws):
    print("Conexão WebSocket aberta")
    # Substitua 'solusdt' pelo par de moedas desejado
    ws.send(json.dumps({"method": "SUBSCRIBE", "params": ["solusdt@ticker"], "id": 1}))

def start_ws():
    websocket.enableTrace(False)  # Desativa o traço de WebSocket para evitar logs detalhados
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

if __name__ == "__main__":
    ws_thread = threading.Thread(target=start_ws)
    ws_thread.start()
