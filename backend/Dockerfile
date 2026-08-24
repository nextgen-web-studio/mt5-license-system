FROM python:3.11-slim

# Install WINE, Xvfb, and Unzip
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y wine wine32 wine64 xvfb unzip wget curl jq && \
    apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Download the ZIP from GitHub Releases, unzip, and clean up
RUN wget -qO metaeditor64.zip "https://github.com/nextgen-web-studio/mt5-license-system/releases/download/compiler-v1.0/metaeditor64.zip" && \
    unzip metaeditor64.zip && \
    rm metaeditor64.zip

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

