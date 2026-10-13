FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r /app/backend/requirements.lock && useradd -m -u 10001 retail
COPY backend /app/backend
COPY fixtures /app/fixtures
RUN mkdir -p /app/backend/media /app/backend/staticfiles && chown -R retail:retail /app
USER retail
WORKDIR /app/backend
EXPOSE 8000
CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","60"]

