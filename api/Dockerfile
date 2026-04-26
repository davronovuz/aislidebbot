FROM python:3.12-slim

WORKDIR /app

# System deps: LibreOffice for PDF conversion, fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fonts-liberation \
    fonts-freefont-ttf \
    libpangocairo-1.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy full project (for shared utils: content_generator, pptx_generator, etc.)
COPY . /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
