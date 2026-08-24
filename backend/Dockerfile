FROM python:3.11-slim

# Install WINE, Xvfb, and Unzip
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y wine wine32 wine64 xvfb unzip wget software-properties-common curl jq && \
    apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# In Render, we can download the ZIP via a startup script to avoid GitHub limits
# For now, this is a placeholder where Render will pull it from external storage
# RUN wget -qO metaeditor64.zip "YOUR_EXTERNAL_URL" && unzip metaeditor64.zip && rm metaeditor64.zip

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
