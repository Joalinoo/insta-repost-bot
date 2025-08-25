import os
import json
import time
import requests
import threading
import google.generativeai as genai
from functools import lru_cache
from scraper import get_latest_posts
from dotenv import load_dotenv
from flask import Flask
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- Carregar variáveis
load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")  # agora fixo no .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

POSTED_FILE = "posted.json"
GRAPH = "https://graph.facebook.com/v21.0"
app = Flask(__name__)

# --- Helpers
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

# --- Postagem
def post_to_instagram(media_url, caption, is_video=False):
    if not ACCESS_TOKEN or not IG_USER_ID:
        print("⚠️ ACCESS_TOKEN ou IG_USER_ID não configurados. Pulei a postagem.")
        return

    try:
        # Criação do container
        container_url = f"{GRAPH}/{IG_USER_ID}/media"
        payload = {
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }

        if is_video:
            payload["media_type"] = "VIDEO"
            payload["video_url"] = media_url
        else:
            payload["image_url"] = media_url

        print(f"🚀 Criando container ({'vídeo' if is_video else 'imagem'})...")
        c = requests.post(container_url, data=payload, timeout=60)
        c.raise_for_status()
        creation_id = c.json().get("id")
        if not creation_id:
            print("❌ Falha: sem creation_id no retorno:", c.text)
            return

        # Publicação
        publish_url = f"{GRAPH}/{IG_USER_ID}/media_publish"
        p = requests.post(
            publish_url,
            data={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
            timeout=60
        )
        p.raise_for_status()
        print("✅ Post publicado com sucesso:", p.json())

    except requests.exceptions.RequestException as e:
        print("❌ Erro de requisição na postagem:", e)
    except Exception as e:
        print("❌ Erro inesperado na postagem:", e)

# --- Loop principal
def bot_main_loop():
    while True:
        try:
            posted = load_posted()
            posts = get_latest_posts()

            for post in posts:
                post_id = post["id"]
                if post_id in posted:
                    continue

                print(f"\n📰 Nova notícia: {post['title']}")
                caption = summarize_with_gemini(post["text"] or "")
                print("📝 Legenda gerada:", caption[:120], "...")

                if post.get("video"):
                    print("🎥 Tentando postar vídeo...")
                    post_to_instagram(post["video"], caption, is_video=True)
                elif post.get("image"):
                    print("🖼️ Tentando postar imagem...")
                    post_to_instagram(post["image"], caption, is_video=False)
                else:
                    print("⚠️ Nenhuma mídia encontrada, pulei.")
                    continue

                posted.append(post_id)
                save_posted(posted)
                time.sleep(60)  # pausa entre posts

        except Exception as e:
            print("💥 Erro no loop principal:", e)

        print("⏳ Aguardando próxima varredura...")
        time.sleep(300)  # 5 min

# --- Servidor keep-alive (Render)
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"🌐 Servidor web rodando na porta {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_main_loop)
    bot_thread.daemon = True
    bot_thread.start()
    run_web_server()
