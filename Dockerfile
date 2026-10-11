FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py admin.py ./
COPY index.html app.js style.css premium.css favicon.svg robots.txt ./
COPY admin.html admin.js admin.css ./
RUN useradd --create-home orbit && mkdir /data && chown orbit:orbit /data
USER orbit
ENV DATABASE_PATH=/data/orbit.sqlite3
EXPOSE 8080
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 app:application"]
