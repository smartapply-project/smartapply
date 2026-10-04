FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
COPY frontend/.npmrc ./
RUN corepack enable && pnpm install --no-frozen-lockfile --allow-build esbuild
COPY frontend/ ./
RUN pnpm build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY public/ ./public/
COPY app.config.ts ./app.config.ts
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN mkdir -p data/uploads
EXPOSE 3000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-3000}"]
