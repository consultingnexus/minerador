# Usa uma imagem oficial do Python estável e leve
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de dependências primeiro
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# --- ADIÇÃO PARA O PLAYWRIGHT ---
# 1. Instala as dependências de sistema do Linux que os navegadores exigem
# 2. Baixa o binário do Chromium/Chrome de forma automatizada
RUN playwright install-deps chromium && \
    playwright install chromium
# ---------------------------------

# Copia todo o conteúdo do projeto para dentro do container
COPY . .

# Comando para rodar o Uvicorn em modo de produção
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]