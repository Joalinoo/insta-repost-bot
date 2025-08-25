import os
import json
import time
import requests
import threading
import google.generativeai as genai
from scraper import get_latest_posts
from dotenv import load_dotenv
from flask import Flask
from http.server import HTTPServer, BaseHTTPRequestHandler

# Carregar variáveis de ambiente
load_dotenv()

# --- Configurações
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")  # ainda guardamos caso precise
IG_USER_ID = os.getenv("IG_USER_ID")  # 🔥 agora fixo do .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

POSTED_FILE = "posted.json"

GRAPH = "https://graph.facebook.com/v21.0"
app = Flask(__name__)

# --- Funções Auxiliares
def load_posted():
    if not os.path.exists(POSTED_FILE):
        return []
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_posted(posted_list):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted_list, f, indent=2, ensure_ascii=False)

def summarize_with_gemini(text):
    genai.configure(api_key=GOOGLE_API_KEY)
    prompt = f"""
    Resuma a seguinte notícia de fofoca em 2 a 3 frases chamativas para Instagram,
    finalize com hashtags populares relacionadas:

    {text}
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

# --- Postagem no Instagram
def post_to_instagram(media_url, caption, media_type="image"):
    if not ACCESS_TOKEN:
        print("⚠️ Nenhum ACCESS_TOKEN configurado. Pulei a postagem.")
        return

    if not IG_USER_ID:
        print("❌ Nenhum IG_USER_ID configurado. Configure no .env")
        return

    try:
        container_url = f"{GRAPH}/{IG_USER_ID}/media"
        container_payload = {
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }

        if media_type == "image":
            container_payload["image_url"] = media_url
        elif media_type == "video":
            container_payload["media_type"] = "VIDEO"
            container_payload["video_url"] = media_url
        else:
            print(f"⚠️ Tipo de mídia não suportado: {media_type}")
            return

        # Cria o container
        c = requests.post(container_url, data=container_payload, timeout=60)
        c.raise_for_status()
        creation_id = c.json().get("id")
        if not creation_id:
            print("❌ Sem creation_id no retorno:", c.text)
            return

        # Publica
        publish_url = f"{GRAPH}/{IG_USER_ID}/media_publish"
        p = requests.post(
            publish_url,
            data={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
            timeout=30
        )
        p.raise_for_status()
        print(f"✅ {media_type.capitalize()} publicado no Instagram:", p.json())

    except requests.exceptions.RequestException as e:
        print("❌ Erro de requisição na postagem:", e)
    except Exception as e:
        print("❌ Erro inesperado na postagem:", e)

# --- Fluxo principal do bot (rodando em thread)
def bot_main_loop():
    while True:
        try:
            posted = load_posted()
            posts = get_latest_posts()

            for post in posts:
                post_id = post["id"]
                if post_id in posted:
                    continue

                print(f"📰 Nova notícia encontrada: {post['title']}")
                caption = summarize_with_gemini(post["text"])
                print("Legenda gerada:", caption)

                # Decide tipo de mídia
                if "video" in post and post["video"]:
                    post_to_instagram(post["video"], caption, media_type="video")
                elif "image" in post and post["image"]:
                    post_to_instagram(post["image"], caption, media_type="image")
                else:
                    print("⚠️ Post sem mídia válida:", post)

                posted.append(post_id)
                save_posted(posted)
                time.sleep(60)

        except Exception as e:
            print("Erro no loop principal:", e)
        time.sleep(300)

# --- Servidor web simples para o Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"✅ Servidor web rodando na porta {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_main_loop)
    bot_thread.daemon = True
    bot_thread.start()
    run_web_server()
