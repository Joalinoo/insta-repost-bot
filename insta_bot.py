import os
import requests
from instagrapi import Client
from datetime import datetime
import tempfile

# -------- Prompt Styles --------
PROMPTS = {
    "choquei": """Transforme a notícia abaixo em uma legenda estilo página de fofoca sensacionalista.
Seja impactante, use emojis 🔥👀💣, crie suspense e estimule comentários.
Adicione 3-6 hashtags virais no final.
Texto-base:\n""",

    "deboche": """Reescreva a notícia abaixo em tom irônico e engraçado, como se fosse um comentário ácido.
Use gírias, sarcasmo e humor. Adicione 3-6 hashtags polêmicas e engraçadas no final.
Texto-base:\n""",

    "serio": """Resuma a notícia abaixo em 1–2 frases diretas em tom neutro, jornalístico.
Sem opinião, apenas informação. Inclua hashtags só de contexto no final.
Texto-base:\n""",

    "default": """Gere uma legenda curta, direta e com alto engajamento para Instagram sobre a notícia abaixo.
Evite citar fontes. Inclua 3-6 hashtags relevantes ao final.
Texto-base:\n"""
}

def safe_filename(s):
    return "".join(c if c.isalnum() else "_" for c in s)[:100]

class InstagramBot:
    def __init__(self, username, password, verification_code="", google_api_key=None):
        self.username = username
        self.password = password
        self.verification_code = verification_code
        self.google_api_key = google_api_key
        self.cl = Client()
        self.logged_in = False

        # Escolhe estilo de legenda (CAPTION_STYLE env var)
        self.caption_style = os.getenv("CAPTION_STYLE", "default").lower()
        if self.caption_style not in PROMPTS:
            self.caption_style = "default"

    # ------------------ Login ------------------
    def ensure_login(self):
        if self.logged_in:
            return
        try:
            self.cl.login(self.username, self.password, verification_code=self.verification_code)
            self.logged_in = True
            print(f"✅ Logado no Instagram como {self.username}")
        except Exception as e:
            print(f"❌ Erro ao logar no Instagram: {e}")
            self.logged_in = False

    # ------------------ AI Caption ------------------
    def generate_ai_caption(self, base_text, fallback=""):
        if not self.google_api_key:
            return fallback

        prompt = PROMPTS.get(self.caption_style, PROMPTS["default"]) + base_text

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.google_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(prompt)
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            print(f"⚠️ Falha usando Gemini: {e}")
        return fallback

    # ------------------ Postar Imagem ------------------
    def post_photo_from_url(self, url, caption):
        self.ensure_login()
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
                f.write(r.content)
                f.flush()
                self.cl.photo_upload(f.name, caption)
            print("📸 Foto enviada com sucesso.")
        except Exception as e:
            print(f"❌ Erro ao postar foto: {e}")

    # ------------------ Postar Vídeo ------------------
    def post_video_from_url(self, url, caption):
        self.ensure_login()
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
                f.write(r.content)
                f.flush()
                self.cl.video_upload(f.name, caption)
            print("🎥 Vídeo enviado com sucesso.")
        except Exception as e:
            print(f"❌ Erro ao postar vídeo: {e}")
