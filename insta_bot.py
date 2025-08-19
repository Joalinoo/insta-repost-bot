# instabot.py
import os
import time
from instagrapi import Client
from loguru import logger
from dotenv import load_dotenv
import schedule

# Carrega variáveis do .env
load_dotenv()
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

# Inicializa cliente Instagram
cl = Client()

def login():
    try:
        cl.login(IG_USERNAME, IG_PASSWORD)
        logger.success("Login feito com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao logar: {e}")

def repost_post(post_url, caption=None):
    try:
        media_id = cl.media_pk_from_url(post_url)
        path = cl.media_download(media_id)
        cl.photo_upload(path, caption or "")
        logger.success(f"Repost realizado com sucesso: {post_url}")
    except Exception as e:
        logger.error(f"Erro ao repostar: {e}")

def job():
    logger.info("Rodando repost diário...")
    # Aqui você coloca os links dos posts que quer repostar
    posts = [
        "https://www.instagram.com/p/EXEMPLO1/",
        "https://www.instagram.com/p/EXEMPLO2/",
    ]
    for post in posts:
        repost_post(post, caption="🔥 repost automático 🔥")

if __name__ == "__main__":
    login()
    # Agenda para rodar todo dia às 09:00
    schedule.every().day.at("09:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(10)

