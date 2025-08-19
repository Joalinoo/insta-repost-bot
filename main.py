import os
import time
import random
import threading
import json
from datetime import datetime
from flask import Flask

from scraper import collect_news_items
from insta_bot import InstagramBot, safe_filename

# --------------- ENV CONFIG ---------------
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
IG_VERIFICATION_CODE = os.getenv("IG_VERIFICATION_CODE", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")  # optional for AI captions

# Comma-separated list of sites. Default: Purepeople home.
SCRAPE_SITES = [s.strip() for s in os.getenv("SCRAPE_SITES", "https://www.purepeople.com.br/,https://ofuxico.com.br/todas-as-noticias/").split(",") if s.strip()]

# Minutes between scraping/post cycles (randomized a bit to look human)
BASE_SLEEP_MIN = int(os.getenv("BASE_SLEEP_MIN", "5"))  # default 5 min
RANDOM_JITTER_MIN = int(os.getenv("RANDOM_JITTER_MIN", "3"))  # +/- jitter

# Max posts per cycle (avoid floods)
MAX_POSTS_PER_CYCLE = int(os.getenv("MAX_POSTS_PER_CYCLE", "2"))

# Hashtags extras (comma-separated)
EXTRA_HASHTAGS = [h.strip() for h in os.getenv("EXTRA_HASHTAGS", "fofoca,choquei,babado,famosos,urgente,brasil").split(",") if h.strip()]

POSTED_DB_FILE = os.getenv("POSTED_DB_FILE", "posted.json")  # tracks URLs already posted

# --------------- RUNTIME STATE ---------------
app = Flask(__name__)
bot = InstagramBot(username=IG_USERNAME, password=IG_PASSWORD, verification_code=IG_VERIFICATION_CODE, google_api_key=GOOGLE_API_KEY)

def load_posted_db():
    if not os.path.exists(POSTED_DB_FILE):
        with open(POSTED_DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return set()
    try:
        with open(POSTED_DB_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        with open(POSTED_DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return set()

def save_posted_db(posted_set):
    try:
        with open(POSTED_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(posted_set)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Erro salvando posted.json: {e}")

POSTED = load_posted_db()

def build_caption(item):
    base = item.get("title", "").strip()
    summary = item.get("summary", "").strip()
    if summary and len(summary) > 20:
        base_line = f"{base} — {summary}"
    else:
        base_line = base

    hashtags = " ".join("#" + h.replace("#","").strip() for h in EXTRA_HASHTAGS[:6])

    caption = bot.generate_ai_caption(base_line, fallback=None)
    if not caption:
        caption = f"{base_line}\n\nO que tu acha disso? Comenta! 👇\n{hashtags}"
    return caption

def process_cycle():
    global POSTED
    print(f"🛰️ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando ciclo de scraping/postagem...")
    print(f"🎭 Estilo de legenda ativo: {bot.caption_style or 'default'}")
    try:
        items = collect_news_items(SCRAPE_SITES, max_items=10)
        new_items = [it for it in items if it.get('url') and it['url'] not in POSTED]
        if not new_items:
            print("ℹ️ Nenhuma notícia nova encontrada.")
            return

        random.shuffle(new_items)
        to_post = new_items[:MAX_POSTS_PER_CYCLE]

        for it in to_post:
            print(f"➡️ Preparando para postar: {it.get('title')} ({it.get('url')})")
            uploaded = False
            if it.get("video_url") and it["video_url"].lower().endswith(".mp4"):
                try:
                    caption = build_caption(it)
                    bot.post_video_from_url(it["video_url"], caption)
                    uploaded = True
                    print("🎬 Vídeo postado com sucesso.")
                except Exception as e:
                    print(f"⚠️ Falha ao postar vídeo (vai tentar imagem): {e}")

            if not uploaded and it.get("image_url"):
                try:
                    caption = build_caption(it)
                    bot.post_photo_from_url(it["image_url"], caption)
                    uploaded = True
                    print("🖼️ Foto postada com sucesso.")
                except Exception as e:
                    print(f"❌ Erro ao postar foto: {e}")

            if uploaded:
                POSTED.add(it["url"])
                save_posted_db(POSTED)
            else:
                print("⚠️ Nada foi postado para este item (sem mídia válida).")
    except Exception as e:
        print(f"❌ Erro no ciclo: {e}")

def loop_runner():
    bot.ensure_login()
    while True:
        hour = datetime.now().hour
        if 2 <= hour <= 6:
            base_sleep = max(BASE_SLEEP_MIN, 30)
            jitter = random.randint(5, 10)
        else:
            base_sleep = BASE_SLEEP_MIN
            jitter = random.randint(-RANDOM_JITTER_MIN, RANDOM_JITTER_MIN)

        process_cycle()

        sleep_minutes = max(1, base_sleep + jitter)
        print(f"⏳ Próximo ciclo em ~{sleep_minutes} minutos.")
        for _ in range(sleep_minutes * 60):
            time.sleep(1)

@app.route('/')
def index():
    return "Scraper + Insta bot ativo 🚀"

threading.Thread(target=loop_runner, daemon=True).start()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
