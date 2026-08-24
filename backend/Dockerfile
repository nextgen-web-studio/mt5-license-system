FROM python:3.11-slim

# Install WINE, Xvfb, and Unzip
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y wine wine32 wine64 xvfb unzip wget software-properties-common && \
    apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Unzip the MetaEditor binary and remove the zip to save space
RUN unzip metaeditor64.zip && rm metaeditor64.zip

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
