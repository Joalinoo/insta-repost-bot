import os
import json
import time
import requests
import threading
from scraper import get_latest_posts
from dotenv import load_dotenv
from http.server import HTTPServer, BaseHTTPRequestHandler

# Carregar variáveis de ambiente
load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")   # da Meta
PAGE_ID = os.getenv("PAGE_ID")             # ID da página vinculada ao Instagram
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Gemini API key

POSTED_FILE = "posted.json"

# ----------------------
# Funções auxiliares
# ----------------------

def load_posted():
    """Carrega lista de posts já publicados para não duplicar."""
    if not os.path.exists(POSTED_FILE):
        return []
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_posted(posted_list):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted_list, f, indent=2, ensure_ascii=False)

def summarize_with_gemini(text):
    """Usa Gemini para resumir/formatar legenda."""
    import google.generativeai as genai
    genai.configure(api_key=GOOGLE_API_KEY)

    prompt = f"""
    Resuma a seguinte notícia de fofoca em 2 a 3 frases chamativas para Instagram,
    finalize com hashtags populares relacionadas:

    {text}
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

def post_to_instagram(image_url, caption):
    """
    Publica no Instagram via Graph API.
    IMPORTANTE: PAGE_ID deve ser da conta que administra o Instagram Business.
    """
    if not ACCESS_TOKEN:
        print("⚠️ Nenhum ACCESS_TOKEN configurado. Pulei a postagem.")
        return

    endpoint = f"https://graph.facebook.com/v21.0/{PAGE_ID}/photos"
    payload = {
        "url": image_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    resp = requests.post(endpoint, data=payload)
    if resp.status_code == 200:
        print("✅ Post enviado com sucesso:", resp.json())
    else:
        print("❌ Erro ao postar:", resp.text)

# ----------------------
# Lógica do bot (rodando em thread)
# ----------------------

def bot_main_loop():
    while True:
        try:
            posted = load_posted()
            posts = get_latest_posts()

            for post in posts:
                post_id = post["id"]
                if post_id in posted:
                    continue  # já postado

                print(f"📰 Nova notícia encontrada: {post['title']}")

                # Gera legenda resumida
                caption = summarize_with_gemini(post["text"])
                print("Legenda gerada:", caption)

                # Publica no Instagram (ou pula se não tiver token)
                post_to_instagram(post["image"], caption)

                # Marca como postado
                posted.append(post_id)
                save_posted(posted)

                time.sleep(60)  # espera 1 min entre posts (evitar flood)

        except Exception as e:
            print("Erro no loop principal:", e)
        time.sleep(300)  # checa a cada 5 min

# ----------------------
# Servidor web simples para o Render
# ----------------------

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_web_server():
    """Mantém uma porta aberta para o Render."""
    port = int(os.environ.get("PORT", 8080))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"✅ Servidor web rodando na porta {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    # Inicia o loop do bot em uma thread separada
    bot_thread = threading.Thread(target=bot_main_loop)
    bot_thread.daemon = True # Garante que a thread será encerrada quando o programa principal for
    bot_thread.start()

    # Inicia o servidor web
    run_web_server()
        
