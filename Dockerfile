# Minimal public placeholder until FastAPI/Next.js replace this service.
FROM python:3.12-alpine

WORKDIR /site
COPY public/index.html ./index.html

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["sh", "-c", "python -m http.server \"${PORT:-8080}\" --bind 0.0.0.0 --directory /site"]
