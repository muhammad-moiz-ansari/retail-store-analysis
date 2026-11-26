# RetailPulse API (no CV stack). Build: docker build -t retailpulse-api .
# Schema and first manager are created explicitly, not at startup:
#   docker run --rm --env-file .env retailpulse-api python -m backend.database --bootstrap-manager
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements-api.txt backend/requirements-api.txt
RUN pip install --no-cache-dir -r backend/requirements-api.txt
COPY backend/ backend/
COPY deploy/entrypoint.sh deploy/entrypoint.sh
# CV weights, recordings and local outputs are not part of the API image.
RUN rm -rf backend/videos backend/output backend/yolov8n.pt backend/interaction/benchmarks backend/interaction/models
RUN useradd --system --no-create-home retailpulse
USER retailpulse
ENV PORT=8011
EXPOSE 8011
CMD ["/app/deploy/entrypoint.sh"]
