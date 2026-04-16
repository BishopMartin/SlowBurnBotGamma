# Minimal placeholder: static docs until FastAPI/Next.js land (see BurnBotGamma-MigrationPlan.md).
FROM python:3.12-alpine

WORKDIR /site
COPY BurnBotGamma-MigrationPlan.md BurnBotBeta-ArchitectureOutline.md ./
COPY docs/ ./docs/
COPY public/index.html ./index.html

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Railway injects PORT at runtime.
CMD ["sh", "-c", "python -m http.server \"${PORT:-8080}\" --bind 0.0.0.0 --directory /site"]
