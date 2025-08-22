from flask import Flask, request

app = Flask(__name__)

# Rota básica pra testar se o server tá vivo
@app.route("/")
def home():
    return "✅ Server Flask rodando no Render!"

# Callback da Meta (para validação e eventos)
@app.route("/callback", methods=["GET", "POST"])
def callback():
    if request.method == "GET":
        # Meta envia GET para validar o webhook
        hub_mode = request.args.get("hub.mode")
        hub_challenge = request.args.get("hub.challenge")
        hub_verify_token = request.args.get("hub.verify_token")

        # Esse verify_token precisa bater com o que tu configurou na Meta
        VERIFY_TOKEN = "meutoken123"

        if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
            return hub_challenge, 200
        else:
            return "❌ Token inválido", 403

    elif request.method == "POST":
        # Quando o Instagram/Facebook mandar eventos, caem aqui
        data = request.json
        print("📩 Evento recebido:", data)
        # Aqui tu pode logar ou até salvar em banco
        return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    # Render expõe via 0.0.0.0
    app.run(host="0.0.0.0", port=5000)
