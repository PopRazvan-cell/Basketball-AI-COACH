FROM python:3.9-slim

# 1. Instalăm dependințele de sistem actualizate
# Am înlocuit libgl1-mesa-glx cu libgl1 și am adăugat biblioteci de suport pentru OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copiem requirements și instalăm pachetele Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiem restul proiectului
COPY . .

# Ne asigurăm că folderul de profile există pentru a nu primi erori la rulare
RUN mkdir -p app/profiles

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
