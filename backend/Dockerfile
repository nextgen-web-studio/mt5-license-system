FROM python:3.11-slim

# Install WINE and Xvfb for MetaEditor
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y wine wine32 wine64 xvfb wget software-properties-common && \
    apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# We will need metaeditor64.exe copied here later!

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
