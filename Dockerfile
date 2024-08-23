
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["gunicorn", "restaurant.wsgi:application", "--bind", "0.0.0.0:8000  & celery -A restaurant worker --loglevel=info"]
