# ========================================
# Stage 1: Build Frontend
# ========================================
FROM node:20-alpine AS frontend

WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY apps/web/ ./

# Build with API pointing to relative path (will be handled by Next.js rewrites)
ENV NEXT_PUBLIC_API_URL=
RUN rm -f playwright.config.ts e2e/**/*.ts
RUN npm run build

# ========================================
# Stage 2: Python Backend
# ========================================
FROM python:3.11-slim AS backend

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ .
RUN mkdir -p /app/data

# ========================================
# Stage 3: Production Image
# ========================================
FROM python:3.11-slim

WORKDIR /app

# Install Node.js and Claude Code CLI
RUN pip install --no-cache-dir nodeenv && \
    nodeenv --node=20.14.0 /opt/nodeenv && \
    . /opt/nodeenv/bin/activate && \
    pip uninstall -y nodeenv
ENV PATH="/opt/nodeenv/bin:$PATH"
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user (Claude Code CLI refuses root with bypassPermissions)
RUN useradd -m -s /bin/bash newhorse

# Copy backend
COPY --from=backend /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin
COPY --from=backend /app /app

# Copy frontend
COPY --from=frontend /app/.next/standalone /app/frontend
COPY --from=frontend /app/.next/static /app/frontend/.next/static
COPY --from=frontend /app/public /app/frontend/public

# Security: remove any secrets that may have leaked into the build context
RUN find /app -name ".env*" -type f -delete 2>/dev/null; \
    rm -rf /app/data/*.db 2>/dev/null; \
    true

# Write docker-compose.yml for "docker compose up" after pulling from registry.
# Repo docker-compose.yml keeps "build: ." for local dev; this one uses "image:" only.
RUN printf '%s\n' \
  'services:' \
  '  newhorse:' \
  '    image: newhorse:latest' \
  '    ports:' \
  '      - "80:80"' \
  '    volumes:' \
  '      - newhorse-data:/app/data' \
  '    environment:' \
  '      - DATABASE_URL=sqlite:///data/newhorse.db' \
  '    restart: unless-stopped' \
  '    healthcheck:' \
  '      test: ["CMD", "curl", "-f", "http://localhost:3999/health"]' \
  '      interval: 30s' \
  '      timeout: 10s' \
  '      retries: 3' \
  'volumes:' \
  '  newhorse-data:' \
  > /docker-compose.yml

ENV PYTHONUNBUFFERED=1
ENV API_PORT=8999
ENV HOST=0.0.0.0
ENV DATABASE_URL=sqlite:///data/newhorse.db

RUN mkdir -p /app/data && chown -R newhorse:newhorse /app

EXPOSE 80 3999

USER newhorse

# Start Next.js frontend on port 80 (handles /api via rewrites)
# Start backend on port 3999
CMD ["sh", "-c", "cd /app/frontend && PORT=80 HOSTNAME=0.0.0.0 node server.js & cd /app && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 3999"]
