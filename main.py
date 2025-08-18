import os
import time
import random
import threading
from instagrapi import Client
import google.generativeai as genai
import re
import json
import csv
from datetime import datetime
from flask import Flask

# --- Configurações de Ambiente ---
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
IG_VERIFICATION_CODE = os.getenv("IG_VERIFICATION_CODE")

# --- Configurações da Máquina ---
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SESSION_FILE = "session.json"
REPOST_LOG_FILE = "repost_log.csv"

# --- Dados de Operação ---
ORIGINS = ["alfinetei", "saiufofoca", "babados", "portalg1"]

# Proxies (Adicione seus próprios proxies aqui)
# Use o formato "http://usuario:senha@ip:porta"
PROXIES = [
    "http://user:pass@ip1:port",
    "http://user:pass@ip2:port",
    "http://user:pass@ip3:port"
]

# Mapeamento de emoções para palavras-chave
EMOTION_MAP = {
    "choque": ["absurdo", "chocante", "inacreditável", "revoltante"],
    "curiosidade": ["descobriu", "segredo", "por que", "entenda"],
    "raiva": ["revolta", "absurdo", "inacreditável", "sem noção"],
    "ganancia": ["dinheiro", "milhões", "oportunidade", "rico"],
}

# --- Lógica de Login e Sessão ---
cl = Client()

def login_and_save_session():
    try:
        print("Tentando login manual...")
        cl.login(USERNAME, PASSWORD)
    except Exception as e:
        if "challenge_required" in str(e):
            if IG_VERIFICATION_CODE:
                try:
                    cl.challenge_code(USERNAME, IG_VERIFICATION_CODE)
                    print("Código de verificação aceito. Sessão salva!")
                except Exception as challenge_e:
                    print("--------------------------------------------------")
                    print("❌ ERRO: O CÓDIGO DE VERIFICAÇÃO É INVÁLIDO OU EXPIROU.")
                    print("⚠️ Insira um novo código na variável IG_VERIFICATION_CODE do Render.")
                    print("--------------------------------------------------")
                    raise challenge_e
            else:
                print("--------------------------------------------------")
                print("❌ ERRO: O SCRIPT PRECISA DE UM CÓDIGO DE VERIFICAÇÃO.")
                print("⚠️ Insira o código na variável IG_VERIFICATION_CODE do Render.")
                print("--------------------------------------------------")
                raise e
        else:
            raise e
    cl.dump_settings(SESSION_FILE)
    print("Sessão salva em session.json. Agora a vida vai ser fácil.")

if os.path.exists(SESSION_FILE):
    try:
        cl.load_settings(SESSION_FILE)
        cl.login(USERNAME, PASSWORD)
        print("🚀 Sessão carregada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao carregar a sessão, tentando login manual... {e}")
        login_and_save_session()
else:
    login_and_save_session()

# --- Lógica de Log de Posts ---
def get_reposted_media_ids():
    if not os.path.exists(REPOST_LOG_FILE):
        return set()
    with open(REPOST_LOG_FILE, 'r') as f:
        reader = csv.reader(f)
        return set(row[0] for row in reader)

def add_reposted_media_id(media_id):
    with open(REPOST_LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([media_id])

processed_media_ids = get_reposted_media_ids()

# --- Funções do Robô ---
def generate_aggressive_caption(original_caption, username):
    detected_emotion = "curiosidade"
    for emotion, keywords in EMOTION_MAP.items():
        for keyword in keywords:
            if keyword in original_caption.lower():
                detected_emotion = emotion
                break
        if detected_emotion != "curiosidade":
            break

    prompt = (
        f"Gere uma legenda para um post de mídia social no estilo 'clickbait' e extremamente agressivo, "
        f"com base na seguinte descrição: '{original_caption}'. O objetivo é manipular o usuário a interagir, "
        f"usando os gatilhos de {detected_emotion}. A legenda deve ser curta, sem menção à fonte original (@{username}), "
        f"e deve incluir um CTA (Chamada para Ação) no final, tipo 'Comenta o que tu acha', "
        f"'Não vai acreditar nisso', etc. Adicione 4 a 6 hashtags populares relacionadas ao tema. "
        f"Exemplo de resposta: 'DESCUBRA AGORA! {original_caption}. Não vai acreditar no final! #fofoca #choquei #babadodosfamosos'"
    )

    try:
        response = model.generate_content(prompt)
        new_caption = response.text.strip()
        
        # Remove menções e URLs geradas pela IA
        new_caption = re.sub(r'@\w+', '', new_caption)
        new_caption = re.sub(r'https?://[^\s]+', '', new_caption)
        
        return new_caption
    except Exception as e:
        print(f"❌ Erro ao gerar legenda com IA: {e}")
        return f"🚨🚨 ALERTA: {original_caption}! 🔥 #fofocanews"

def repost_from_origin(username):
    try:
        user_id = cl.user_id_from_username(username)
        medias = cl.user_medias(user_id, 10) # Pega os 10 posts mais recentes

        # --- Filtro para Mídias Válidas ---
        valid_medias = []
        for m in medias:
            try:
                if str(m.pk) not in processed_media_ids and m.caption_text and hasattr(m, 'clip_metadata'):
                    valid_medias.append(m)
            except Exception as e:
                print(f"⚠️ Mídia inválida ignorada: {e}")
        
        medias = valid_medias
        
        if not medias:
            print(f"Nenhum post novo de @{username} para repostar.")
            return

        # Ordena os posts pelo número de curtidas para usar a alavancagem
        medias.sort(key=lambda x: x.like_count, reverse=True)
        media_to_repost = medias[0]

        # Adiciona lógica de proxy (se a lista não estiver vazia)
        if PROXIES:
            proxy = random.choice(PROXIES)
            cl.set_proxy(proxy)
            print(f"✅ Usando proxy: {proxy}")

        original_caption = media_to_repost.caption_text
        new_caption = generate_aggressive_caption(original_caption, username)

        if media_to_repost.media_type == 1:
            path = cl.photo_download(media_to_repost.pk)
            cl.photo_upload(path, new_caption)
            print(f"🚀 Repost de foto de @{username} feito com sucesso!")

        elif media_to_repost.media_type == 2:
            path = cl.video_download(media_to_repost.pk)
            cl.video_upload(path, new_caption)
            print(f"🚀 Repost de vídeo de @{username} feito com sucesso!")

        add_reposted_media_id(str(media_to_repost.pk))
        # Limpa os arquivos baixados pra não ocupar espaço
        os.remove(path)

    except Exception as e:
        print(f"❌ Erro ao repostar de @{username}: {e}")

# --- Loop Principal de Operação (com horários humanos) ---
def start_bot_loop():
    while True:
        hora = datetime.now().hour
        if 2 <= hora <= 6:
            # Frequência menor de madrugada
            sleep_time = random.randint(3600, 5400) # 1h a 1h30
            print(f"😴 Madrugada, dormindo por {sleep_time/60:.2f} minutos.")
        else:
            # Frequência normal
            sleep_time = random.randint(1200, 2400) # 20 a 40 minutos
            print(f"⏰ Horário comercial, próximo post em {sleep_time/60:.2f} minutos.")

        random.shuffle(ORIGINS) # Randomiza a ordem pra parecer humano
        for origin in ORIGINS:
            repost_from_origin(origin)

        # Adiciona o contador regressivo antes do sleep
        for remaining_time in range(sleep_time, 0, -1):
            if remaining_time % 60 == 0:
                print(f"Próxima postagem em {remaining_time // 60} minutos...")
            time.sleep(1)

# --- Servidor de fachada para o Render ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot está rodando 🚀"

# Inicia o loop do bot em background
threading.Thread(target=start_bot_loop, daemon=True).start()

# Inicia o servidor Flask como processo principal
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
