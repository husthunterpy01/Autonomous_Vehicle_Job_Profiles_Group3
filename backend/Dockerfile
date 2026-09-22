FROM python:3.10-slim

WORKDIR /app

# Install deps first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual app code
COPY ./app ./app

# app/middleware/logging.py writes a RotatingFileHandler to the relative
# path "app.log" (i.e. /app/app.log at runtime) - appuser needs write access
# to /app for that, since COPY defaults everything to root ownership.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
