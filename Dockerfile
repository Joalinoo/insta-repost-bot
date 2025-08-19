# Usa uma imagem base oficial do Python
FROM python:3.12-slim

# Instala as dependências do sistema necessárias para o Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Instala as dependências do Python
RUN pip install -r requirements.txt

# Comando para rodar a aplicação
CMD ["python", "main.py"]
