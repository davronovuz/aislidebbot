FROM python:3.12-slim

WORKDIR /app

# LibreOffice for PDF conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fonts-liberation \
    fonts-freefont-ttf \
    libpangocairo-1.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "app.py"]
