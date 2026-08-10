# Works on Fly.io, Render, Koyeb, Cloud Run — anywhere that takes a container.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Pillow needs these at runtime for JPEG/PNG/WebP handling.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo zlib1g libwebp7 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files are built into the image. A dummy key is fine here: this runs at
# build time with no database and no secrets available.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

# Never run as root.
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Migrations run on boot so a deploy cannot serve a schema it does not have.
CMD sh -c "python manage.py migrate --noinput && \
           gunicorn chainreaction.wsgi:application \
             --bind 0.0.0.0:${PORT} \
             --workers 3 \
             --timeout 60 \
             --access-logfile - \
             --error-logfile -"
