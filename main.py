import os
import time
from instagrapi import Client
import google.generativeai as genai
import re
import json
import csv

# Login
USERNAME = os.getenv("IG_USERNAME")
PASSWORD = os.getenv("IG_PASSWORD")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Adiciona a variável para o código de verificação
IG_VERIFICATION_CODE = os.getenv("IG_VERIFICATION_CODE")

# Configuração da API do Google Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Adiciona o arquivo da sessão e do log de posts
SESSION_FILE = "session.json"
REPOST_LOG_FILE = "repost_log.csv"

cl = Client()

def login_and_save_session():
    # Tenta o login com a senha
    try:
        print("Tentando login manual...")
        cl.login(USERNAME, PASSWORD)
    except Exception as e:
        # Se falhar, tenta o código de verificação do Render
        if "challenge_required" in str(e):
            if IG_VERIFICATION_CODE:
                try:
                    cl.challenge_code(USERNAME, IG_VERIFICATION_CODE)
                    print("Código de verificação aceito. Sessão salva!")
                except Exception as challenge_e:
                    # Se o código do Render for inválido, avisa o erro
                    print("--------------------------------------------------")
                    print("❌ ERRO: O CÓDIGO DE VERIFICAÇÃO É INVÁLIDO OU EXPIROU.")
                    print("⚠️ O script precisa de um novo código de verificação válido. Verifique seu e-mail/SMS e insira o novo código na variável IG_VERIFICATION_CODE do Render.")
                    print("--------------------------------------------------")
                    raise challenge_e
            else:
                # Se não tiver código no Render, avisa
                print("--------------------------------------------------")
                print("❌ ERRO: O SCRIPT PRECISA DE UM CÓDIGO DE VERIFICAÇÃO.")
                print("⚠️ Insira o código que foi enviado para o seu e-mail/SMS na variável IG_VERIFICATION_CODE do Render.")
                print("--------------------------------------------------")
                raise e
        else:
            raise e
    # Salva a sessão em um arquivo
    cl.dump_settings(SESSION_FILE)
    print("Sessão salva em session.json. Agora a vida vai ser fácil.")

# Lógica de login e salvamento de sessão
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

# Lógica do log de posts
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

# Lista de contas de onde vamos puxar os conteúdos
ORIGINS = ["alfinetei", "saiufofoca", "babados", "portalg1"]

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
        # Tenta pegar os 5 posts mais recentes para buscar por algo não republicado
        medias = cl.user_medias(user_id, 5) 

        # Ordena os posts pelo número de curtidas para usar a alavancagem
        medias.sort(key=lambda x: x.like_count, reverse=True)

        for media in medias:
            if str(media.pk) in processed_media_ids:
                print(f"Post {media.pk} de @{username} já foi repostado. Pulando...")
                continue
            
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

            add_reposted_media_id(str(media.pk))
            # Reposta apenas um por vez para evitar spam e garantir a qualidade
            break 
    except Exception as e:
        print(f"❌ Erro ao repostar de @{username}: {e}")

# Loop infinito: verifica todas as contas a cada 30 min
while True:
    for origin in ORIGINS:
        repost_from(origin)
    time.sleep(60 * 30)

