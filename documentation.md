# Documentação do Bot Insta-Repost

## Correções e Melhorias

### 1. Desativação da Postagem de Vídeos

Para resolver os problemas de postagem de vídeos e focar apenas na postagem de imagens, a lógica de postagem de vídeos foi comentada no arquivo `main.py`. Isso garante que o bot tentará postar apenas imagens, ignorando qualquer conteúdo de vídeo.

**Local da alteração:** `insta-repost-bot-main/main.py`

**Trecho alterado:**
```python
                # if post.get("video"):
                #     print("🎥 Tentando postar vídeo...")
                #     post_to_instagram(post["video"], caption, is_video=True)
                if post.get("image"):
                    print("🖼️ Tentando postar imagem...")
                    post_to_instagram(post["image"], caption, is_video=False)
```

### 2. Correção da URL do Scraper

A URL `https://www.purepeople.com.br/noticias` estava retornando um erro 404, o que impedia o bot de coletar novas notícias. Esta URL foi removida da lista de sites a serem "scrapeados" no arquivo `scraper.py`, mantendo apenas a URL funcional `https://www.purepeople.com.br/famosos`.

**Local da alteração:** `insta-repost-bot-main/scraper.py`

**Trecho alterado:**
```python
    sites_to_scrape = [
        "https://www.purepeople.com.br/famosos"
    ]
```

### 3. Configuração de Variáveis de Ambiente

Foi criado um arquivo `.env` na raiz do projeto (`insta-repost-bot-main/.env`) para armazenar as variáveis de ambiente sensíveis (`ACCESS_TOKEN`, `IG_USER_ID`, `GOOGLE_API_KEY`). Isso melhora a segurança e facilita a configuração do bot em diferentes ambientes.

**Local do arquivo:** `insta-repost-bot-main/.env`

**Conteúdo do arquivo `.env`:**
```
ACCESS_TOKEN=SEU_ACCESS_TOKEN
IG_USER_ID=SEU_IG_USER_ID
GOOGLE_API_KEY=SUA_GOOGLE_API_KEY
```

## Funcionamento Atual

O bot agora executa as seguintes etapas:

1.  **Coleta de Notícias:** Realiza o "scraping" de notícias do site Purepeople (apenas da seção de famosos) para identificar novos posts.
2.  **Verificação de Duplicidade:** Verifica se a notícia já foi postada anteriormente usando o arquivo `posted.json`.
3.  **Geração de Legenda:** Utiliza a API do Google Gemini para gerar uma legenda chamativa e com hashtags para a notícia.
4.  **Postagem de Imagens:** Tenta postar a imagem associada à notícia no Instagram, utilizando o `ACCESS_TOKEN` e `IG_USER_ID` fornecidos.
5.  **Servidor Keep-Alive:** Mantém um servidor web simples rodando para garantir que o bot permaneça ativo em ambientes como o Render.






### 4. Limitações da API do Instagram e Reversão das Melhorias de Imagem

Foi identificado que a API do Instagram Graph para postagem de imagens exige que a imagem esteja hospedada em uma URL pública. As tentativas de processar a imagem localmente (melhoria de qualidade e enquadramento) e depois enviá-la diretamente para a API resultaram em erros (HTTP 400 Bad Request), pois a API não aceita o upload direto de arquivos binários para o endpoint de postagem de imagens.

Devido a essa limitação, as funcionalidades de melhoria de qualidade e enquadramento de imagem foram revertidas. O bot agora posta as imagens utilizando as URLs originais fornecidas pelo scraper. Para implementar as melhorias de imagem, seria necessário um serviço de hospedagem de imagens externo para processar e disponibilizar as imagens em uma URL pública antes da postagem no Instagram.

**Local da alteração:** `insta-repost-bot-main/main.py` (reversão das funções `process_image` e alterações em `post_to_instagram`)

**Dependências removidas:** `opencv-python` (removido do `requirements.txt`)


