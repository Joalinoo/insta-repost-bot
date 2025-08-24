import os
import json
import time
import requests
import threading
import google.generativeai as genai
from functools import lru_cache
from scraper import get_latest_posts
from dotenv import load_dotenv
from flask import Flask, jsonify
from http.server import HTTPServer, BaseHTTPRequestHandler

# Carregar variáveis de ambiente
load_dotenv()

# --- Configurações
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
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

@lru_cache(maxsize=1)
def get_ig_user_id(page_id, access_token):
    url = f"{GRAPH}/{page_id}"
    params = {
        "fields": "instagram_business_account{id}",
        "access_token": access_token
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        ig = data.get("instagram_business_account", {})
        ig_id = ig.get("id")
        if not ig_id:
            raise RuntimeError(f"PAGE_ID sem instagram_business_account vinculado. Resp: {data}")
        return ig_id
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição ao obter IG User ID: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado ao obter IG User ID: {e}")
        return None

def post_to_instagram(image_url, caption):
    if not ACCESS_TOKEN:
        print("⚠️ Nenhum ACCESS_TOKEN configurado. Pulei a postagem.")
        return

    try:
        ig_user_id = get_ig_user_id(PAGE_ID, ACCESS_TOKEN)
        if not ig_user_id:
            return

        # 1) Cria o container
        container_url = f"{GRAPH}/{ig_user_id}/media"
        container_payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }
        c = requests.post(container_url, data=container_payload, timeout=30)
        c.raise_for_status()
        creation_id = c.json().get("id")
        if not creation_id:
            print("❌ Sem creation_id no retorno:", c.text)
            return

        # 2) Publica
        publish_url = f"{GRAPH}/{ig_user_id}/media_publish"
        p = requests.post(publish_url, data={"creation_id": creation_id, "access_token": ACCESS_TOKEN}, timeout=30)
        p.raise_for_status()
        print("✅ Post publicado no Instagram:", p.json())

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
                post_to_instagram(post["image"], caption)
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
