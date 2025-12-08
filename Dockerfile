# Usa uma imagem leve do Python
FROM python:3.10-slim

# Define diretório de trabalho
WORKDIR /app

# Copia e instala requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY . .

# Comando para rodar a aplicação
CMD ["python", "app.py"]