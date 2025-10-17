# Deployment Guide 🚀

Complete guide for deploying Bank of Baku RAG Assistant to production.

## Quick Deploy

### 1. Prerequisites
- Docker & Docker Compose installed
- `.env` file with `LLM_API_KEY`
- Port 5001 available

### 2. One-Command Deploy
```bash
docker-compose up -d
```

That's it! Your application is now running on **http://your-server:5001**

## Detailed Deployment Steps

### Step 1: Prepare Environment

```bash
# Clone repository
git clone https://github.com/your-repo/banking_assistant.git
cd banking_assistant

# Create .env file
cat > .env << EOF
LLM_API_KEY=your_gemini_api_key_here
EOF
```

### Step 2: Build Docker Image

```bash
# Build the image
docker-compose build

# This will:
# - Install Python 3.11
# - Install all dependencies
# - Copy application code
# - Set up environment
```

### Step 3: Run Container

```bash
# Run in foreground (for testing)
docker-compose up

# Run in background (production)
docker-compose up -d
```

### Step 4: Verify Deployment

```bash
# Check if container is running
docker-compose ps

# Check health
curl http://localhost:5001/api/health

# View logs
docker-compose logs -f
```

Expected output:
```json
{
  "status": "healthy",
  "indexed_chunks": 13
}
```

## Production Best Practices

### 1. Use Environment Variables

```bash
# .env file
LLM_API_KEY=your_production_api_key
FLASK_ENV=production
```

### 2. Set Resource Limits

Edit `docker-compose.yml`:
```yaml
services:
  web:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. Enable Logging

```yaml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. Use Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Add SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## Cloud Deployment

### Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

### Deploy to Render

1. Connect GitHub repository
2. Select "Docker" as environment
3. Set environment variables
4. Deploy

### Deploy to DigitalOcean

```bash
# Create droplet
doctl compute droplet create bank-rag \
  --image docker-20-04 \
  --size s-1vcpu-1gb \
  --region nyc1

# SSH into droplet
ssh root@your-droplet-ip

# Clone and run
git clone https://github.com/your-repo/banking_assistant.git
cd banking_assistant
docker-compose up -d
```

### Deploy to AWS ECS

1. Build and push image to ECR
2. Create ECS task definition
3. Create ECS service
4. Configure load balancer

## Monitoring

### Health Checks

```bash
# Built-in health endpoint
curl http://localhost:5001/api/health

# Docker health status
docker-compose ps
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific time range
docker-compose logs --since 1h
```

### Resource Usage

```bash
# Container stats
docker stats bank_rag_assistant

# Disk usage
docker system df
```

## Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose up --build -d
```

### Backup Data

```bash
# Backup scraped data
tar -czf backup-$(date +%Y%m%d).tar.gz scraper/output/

# Restore
tar -xzf backup-20250101.tar.gz
```

### Clean Up

```bash
# Remove stopped containers
docker-compose down

# Remove all (including volumes)
docker-compose down -v

# Clean Docker system
docker system prune -a
```

## Scaling

### Horizontal Scaling (Multiple Instances)

```yaml
services:
  web:
    # ... existing config ...
    deploy:
      replicas: 3
```

### Load Balancing with Nginx

```nginx
upstream bank_rag {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}

server {
    location / {
        proxy_pass http://bank_rag;
    }
}
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs web

# Common issues:
# 1. Port already in use → Change port in docker-compose.yml
# 2. Missing .env file → Create .env with LLM_API_KEY
# 3. Data not found → Ensure scraper/output/rag_chunks.jsonl exists
```

### High Memory Usage

```bash
# Limit memory in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
```

### Slow Performance

```bash
# Check container resources
docker stats

# Optimize:
# 1. Increase CPU/memory limits
# 2. Use persistent ChromaDB storage
# 3. Enable caching
```

## Security

### 1. Don't Expose .env

```bash
# Add to .gitignore
echo ".env" >> .gitignore
```

### 2. Use Secrets Management

```yaml
services:
  web:
    secrets:
      - llm_api_key

secrets:
  llm_api_key:
    external: true
```

### 3. Run as Non-Root User

Add to Dockerfile:
```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

### 4. Update Dependencies Regularly

```bash
# Update requirements
pip list --outdated
pip install -U <package>

# Rebuild
docker-compose up --build -d
```

## Cost Optimization

### 1. Use Smaller Base Image

```dockerfile
FROM python:3.11-slim-alpine
```

### 2. Multi-Stage Build

```dockerfile
FROM python:3.11 as builder
# Build dependencies

FROM python:3.11-slim
# Copy only what's needed
```

### 3. Cache Dependencies

```dockerfile
# Copy requirements first
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code later (better caching)
COPY . .
```

## Monitoring & Alerts

### Uptime Monitoring

Use services like:
- UptimeRobot (free)
- Pingdom
- Better Uptime

### Error Tracking

Integrate Sentry:
```python
import sentry_sdk
sentry_sdk.init(dsn="your-sentry-dsn")
```

### Analytics

Track usage with:
- Google Analytics
- Plausible
- Umami

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify health: `curl http://localhost:5001/api/health`
3. Review this guide
4. Open GitHub issue

---

**Ready for production!** 🚀

Deploy with: `docker-compose up -d`
