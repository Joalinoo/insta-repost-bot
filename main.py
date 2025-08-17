import os
import time
from instagrapi import Client
import google.generativeai as genai
import re

# Login
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configuração da API do Google Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

cl = Client()
cl.login(USERNAME, PASSWORD)

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
