FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force keyrings.alt plaintext backend — no desktop keyring daemon in container
ENV PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring

COPY *.py ./
COPY burnBot_config.ini ./

CMD ["python3", "burnBot.py"]
