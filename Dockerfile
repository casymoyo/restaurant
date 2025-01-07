FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install redis


COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["gunicorn", "resturant.wsgi:application", "--bind", "0.0.0.0:8000"]
