FROM python:3.11-slim

WORKDIR /app

# LibreOffice for PDF conversion, poppler-utils for pdftoppm (page previews)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    poppler-utils \
    fonts-liberation \
    fonts-freefont-ttf \
    libpangocairo-1.0-0 \
    curl \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "app.py"]
