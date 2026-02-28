# Deployment Guide

This guide covers deploying Newhorse to production.

## Production Configuration

### Environment Variables

```bash
# Required
API_PORT=8080
DATABASE_URL=mysql+pymysql://user:pass@host:3306/newhorse
PROJECTS_ROOT=/data/projects
THS_TIER=prod

# Recommended for multi-worker
REDIS_URL=redis://localhost:6379/0

# Optional
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### Database

For production, use MySQL instead of SQLite:

```bash
DATABASE_URL=mysql+pymysql://user:password@host:3306/newhorse?charset=utf8mb4
```

### Redis (Recommended)

Enable Redis for:
- WebSocket message broadcasting across workers
- Session state sharing
- Caching

```bash
REDIS_URL=redis://localhost:6379/0
```

## Docker Deployment

### Dockerfile (Backend)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY apps/api/app ./app

# Run with gunicorn
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080"]
```

### Dockerfile (Frontend)

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

CMD ["npm", "start"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=mysql+pymysql://user:pass@db:3306/newhorse
      - REDIS_URL=redis://redis:6379/0
      - THS_TIER=prod
    depends_on:
      - db
      - redis

  web:
    build:
      context: .
      dockerfile: docker/web.Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - api

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: newhorse
      MYSQL_USER: user
      MYSQL_PASSWORD: pass
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  mysql_data:
  redis_data:
```

## Gunicorn Configuration

Create `apps/api/gunicorn.conf.py`:

```python
bind = "0.0.0.0:8080"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
```

Run:
```bash
gunicorn app.main:app -c gunicorn.conf.py
```

## Reverse Proxy (Nginx)

```nginx
upstream api {
    server localhost:8999;
}

upstream web {
    server localhost:3999;
}

server {
    listen 80;
    server_name your-domain.com;

    location /api {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://web;
        proxy_set_header Host $host;
    }
}
```

## Health Checks

The API provides a health endpoint:

```bash
curl http://localhost:8999/health
# {"ok": true, "service": "newhorse"}
```

## Monitoring

### Metrics

Add Prometheus metrics by installing:
```bash
pip install prometheus-client
```

### Logging

Configure structured logging for production:

```python
# In app/core/logging.py
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })
```

## Security Checklist

- [ ] Use HTTPS in production
- [ ] Set secure CORS origins
- [ ] Enable rate limiting
- [ ] Use strong database passwords
- [ ] Keep dependencies updated
- [ ] Enable authentication (if needed)
- [ ] Regular backups
