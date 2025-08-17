import os
import time
from instagrapi import Client
import google.generativeai as genai
import re
import json

# Login
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configuração da API do Google Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Adiciona o arquivo da sessão
SESSION_FILE = "session.json"

cl = Client()

def login_and_save_session():
    # Tenta o login com a senha
    try:
        print("Tentando login manual...")
        cl.login(USERNAME, PASSWORD)
    except Exception as e:
        # Se falhar, pede o código de verificação
        if "challenge_required" in str(e):
            verification_code = input("O Instagram pediu um código de verificação. Digite o código que foi enviado para o seu e-mail/SMS: ")
            cl.challenge_code(USERNAME, verification_code)
            print("Código aceito. Sessão salva!")
        else:
            raise e
    # Salva a sessão em um arquivo
    cl.dump_settings(SESSION_FILE)
    print("Sessão salva em session.json. Agora a vida vai ser fácil.")

# Lógica de login e salvamento de sessão
if os.path.exists(SESSION_FILE):
    # Tenta carregar a sessão salva
    try:
        cl.load_settings(SESSION_FILE)
        cl.login(USERNAME, PASSWORD)
        print("🚀 Sessão carregada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao carregar a sessão, tentando login manual... {e}")
        login_and_save_session()
else:
    login_and_save_session()


# Lista de contas de onde vamos puxar os conteúdos
ORIGINS = ["alfinetei", "saiufofoca", "babados", "portalg1"]

processed_media_ids = set()

# Mapeamento de emoções para palavras-chave
EMOTION_MAP = {
    "choque": ["absurdo", "chocante", "inacreditável", "revoltante"],
    "curiosidade": ["descobriu", "segredo", "por que", "entenda"],
    "raiva": ["revolta", "absurdo", "inacreditável", "sem noção"],
    "ganancia": ["dinheiro", "milhões", "oportunidade", "rico"],
}

def generate_aggressive_caption(original_caption, username):
    detected_emotion = "curiosidade"
    for emotion, keywords in EMOTION_MAP.items():
        for keyword in keywords:
            if keyword in original_caption.lower():
                detected_emotion = emotion
                break
        if detected_emotion != "curiosidade":
            break

    prompt = f"Gere uma legenda para um post de mídia social no estilo 'clickbait' e extremamente agressivo, com base na seguinte descrição: '{original_caption}'. O objetivo é manipular o usuário a interagir, usando os gatilhos de {detected_emotion}. A legenda deve ser curta, sem menção à fonte original (@{username}), e deve incluir um CTA (Chamada para Ação) no final, tipo 'Comenta o que tu acha', 'Não vai acreditar nisso', etc."

    try:
        response = model.generate_content(prompt)
        new_caption = response.text.strip()
        
        new_caption = re.sub(r'@\w+', '', new_caption)
        
        return new_caption
    except Exception as e:
        print(f"❌ Erro ao gerar legenda com IA: {e}")
        return f"🚨🚨 ALERTA: {original_caption}! 🔥"

def repost_from(username):
    try:
        user_id = cl.user_id_from_username(username)
        medias = cl.user_medias(user_id, 1)
        if not medias or medias[0].pk in processed_media_ids:
            return

        media = medias[0]
        processed_media_ids.add(media.pk)
        
        original_caption = media.caption_text or f"Conteúdo da @{username}"
        new_caption = generate_aggressive_caption(original_caption, username)

        if media.media_type == 1:
            path = cl.photo_download(media.pk)
            cl.photo_upload(path, new_caption)
            print(f"🚀 Repost de foto de @{username} feito com sucesso com legenda manipuladora!")

        elif media.media_type == 2:
            path = cl.video_download(media.pk)
            cl.video_upload(path, new_caption)
            print(f"🚀 Repost de vídeo de @{username} feito com sucesso com legenda manipuladora!")

    except Exception as e:
        print(f"❌ Erro ao repostar de @{username}: {e}")

# Loop infinito: verifica todas as contas a cada 30 min
while True:
    for origin in ORIGINS:
        repost_from(origin)
    time.sleep(60 * 30)
