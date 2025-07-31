# Deployment Guide

Comprehensive deployment guide for the KMS-SFDC Vector Database system in production environments.

## Overview

This guide covers deploying the KMS-SFDC system for production use, including infrastructure requirements, security considerations, monitoring setup, and maintenance procedures.

## 🏗️ Architecture Overview

### Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Production Environment                  │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer (nginx/HAProxy)                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   API Server    │  │   API Server    │  │  Admin UI    │ │
│  │   (Port 8008)   │  │   (Port 8009)   │  │ (Port 4001)  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Vector Database │  │    Scheduler    │  │   Backup     │ │
│  │   (FAISS)       │  │    Service      │  │   Storage    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Monitoring    │  │     Logging     │  │   Metrics    │ │
│  │  (Prometheus)   │  │  (ELK Stack)    │  │  (Grafana)   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- **CPU**: 8 cores (x86_64)
- **RAM**: 16GB (32GB recommended for large datasets)
- **Storage**: 500GB SSD (for vector indexes and backups)
- **Network**: 1Gbps connection
- **OS**: Ubuntu 20.04 LTS or CentOS 8+

**Recommended Requirements:**
- **CPU**: 16 cores with AVX2 support
- **RAM**: 64GB 
- **Storage**: 2TB NVMe SSD
- **Network**: 10Gbps connection
- **GPU**: Optional NVIDIA GPU for faster embeddings (future)

### Software Dependencies

```bash
# System packages
sudo apt update
sudo apt install -y python3.11 python3.11-dev python3.11-venv
sudo apt install -y build-essential pkg-config
sudo apt install -y nginx redis-server postgresql
sudo apt install -y supervisor htop iotop

# Install UV (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 🚀 Deployment Methods

### Method 1: Traditional Server Deployment

#### 1. Server Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash kms-sfdc
sudo usermod -aG sudo kms-sfdc

# Create application directories
sudo mkdir -p /opt/kms-sfdc
sudo mkdir -p /var/log/kms-sfdc
sudo mkdir -p /var/lib/kms-sfdc/data
sudo mkdir -p /var/lib/kms-sfdc/backups

# Set ownership
sudo chown -R kms-sfdc:kms-sfdc /opt/kms-sfdc
sudo chown -R kms-sfdc:kms-sfdc /var/log/kms-sfdc
sudo chown -R kms-sfdc:kms-sfdc /var/lib/kms-sfdc
```

#### 2. Application Deployment

```bash
# Switch to application user
sudo su - kms-sfdc

# Clone repository
cd /opt/kms-sfdc
git clone <repository-url> .

# Setup Python environment
uv venv --python 3.11
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
uv pip install gunicorn supervisor

# Setup configuration
cp .env.example .env
# Edit .env with production values

# Build initial index
make build-index

# Build admin UI
cd admin-ui
npm ci --production
npm run build
cd ..
```

#### 3. Service Configuration

**Gunicorn Configuration** (`/opt/kms-sfdc/gunicorn.conf.py`):
```python
bind = "127.0.0.1:8008"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5
user = "kms-sfdc"
group = "kms-sfdc"
tmp_upload_dir = None
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'default': {
            'formatter': 'default',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['default']
    },
    'loggers': {
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['default'],
            'propagate': 1,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['default'],
            'propagate': 0,
        },
    }
}
```

**Systemd Service** (`/etc/systemd/system/kms-sfdc-api.service`):
```ini
[Unit]
Description=KMS-SFDC Vector Database API
After=network.target
Requires=network.target

[Service]
Type=forking
User=kms-sfdc
Group=kms-sfdc
WorkingDirectory=/opt/kms-sfdc
Environment=PATH=/opt/kms-sfdc/.venv/bin
ExecStart=/opt/kms-sfdc/.venv/bin/gunicorn -c gunicorn.conf.py src.search.api:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Scheduler Service** (`/etc/systemd/system/kms-sfdc-scheduler.service`):
```ini
[Unit]
Description=KMS-SFDC Scheduler Service
After=network.target kms-sfdc-api.service
Requires=network.target

[Service]
Type=simple
User=kms-sfdc
Group=kms-sfdc
WorkingDirectory=/opt/kms-sfdc
Environment=PATH=/opt/kms-sfdc/.venv/bin
ExecStart=/opt/kms-sfdc/.venv/bin/python -m src.scheduler.scheduler_service
Restart=always
RestartSec=10
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

#### 4. Nginx Configuration

**Main Config** (`/etc/nginx/sites-available/kms-sfdc`):
```nginx
upstream kms_sfdc_api {
    server 127.0.0.1:8008 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8009 max_fails=3 fail_timeout=30s backup;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-domain.crt;
    ssl_certificate_key /etc/ssl/private/your-domain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # API endpoints
    location /api/ {
        proxy_pass http://kms_sfdc_api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # Admin UI
    location / {
        root /opt/kms-sfdc/admin-ui/dist;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Health check endpoint (no auth required)
    location /health {
        proxy_pass http://kms_sfdc_api/health;
        access_log off;
    }
}
```

#### 5. Enable Services

```bash
# Enable and start services
sudo systemctl enable kms-sfdc-api
sudo systemctl enable kms-sfdc-scheduler
sudo systemctl enable nginx

sudo systemctl start kms-sfdc-api
sudo systemctl start kms-sfdc-scheduler
sudo systemctl start nginx

# Check service status
sudo systemctl status kms-sfdc-api
sudo systemctl status kms-sfdc-scheduler
```

### Method 2: Docker Deployment

#### 1. Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create app user
RUN useradd -m -u 1000 kms-sfdc
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .
RUN chown -R kms-sfdc:kms-sfdc /app

# Switch to app user
USER kms-sfdc

# Expose port
EXPOSE 8008

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8008/health || exit 1

# Start command
CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.search.api:app"]
```

**Docker Compose** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8008:8008"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  scheduler:
    build: .
    command: ["python", "-m", "src.scheduler.scheduler_service"]
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    depends_on:
      - api
  
  admin-ui:
    image: node:18-alpine
    working_dir: /app
    command: sh -c "npm ci && npm run build && npx serve -s dist -l 4001"
    volumes:
      - ./admin-ui:/app
    ports:
      - "4001:4001"
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - api
      - admin-ui
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    restart: unless-stopped

volumes:
  redis_data:
  prometheus_data:
  grafana_data:
```

#### 2. Deploy with Docker Compose

```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f scheduler

# Scale API service
docker-compose up -d --scale api=3
```

### Method 3: Kubernetes Deployment

#### 1. Kubernetes Manifests

**Namespace** (`k8s/namespace.yaml`):
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kms-sfdc
```

**ConfigMap** (`k8s/configmap.yaml`):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kms-sfdc-config
  namespace: kms-sfdc
data:
  config.yaml: |
    api:
      host: "0.0.0.0"
      port: 8008
      title: "KMS-SFDC Vector Database API"
      version: "1.0.0"
    vectordb:
      model_name: "nomic-embed-text-v1.5"
      index_type: "IndexFlatIP"
      dimension: 768
      index_path: "/app/data/faiss_index.bin"
      metadata_path: "/app/data/case_metadata.json"
```

**Secret** (`k8s/secret.yaml`):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: kms-sfdc-secrets
  namespace: kms-sfdc
type: Opaque
stringData:
  sfdc_username: "your-username"
  sfdc_password: "your-password"
  sfdc_security_token: "your-token"
  sfdc_login_url: "https://login.salesforce.com"
```

**Deployment** (`k8s/deployment.yaml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kms-sfdc-api
  namespace: kms-sfdc
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kms-sfdc-api
  template:
    metadata:
      labels:
        app: kms-sfdc-api
    spec:
      containers:
      - name: api
        image: kms-sfdc:latest
        ports:
        - containerPort: 8008
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: SFDC_USERNAME
          valueFrom:
            secretKeyRef:
              name: kms-sfdc-secrets
              key: sfdc_username
        - name: SFDC_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kms-sfdc-secrets
              key: sfdc_password
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: data
          mountPath: /app/data
        livenessProbe:
          httpGet:
            path: /health
            port: 8008
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8008
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "2Gi"
            cpu: "500m"
          limits:
            memory: "8Gi"
            cpu: "2"
      volumes:
      - name: config
        configMap:
          name: kms-sfdc-config
      - name: data
        persistentVolumeClaim:
          claimName: kms-sfdc-data
```

**Service** (`k8s/service.yaml`):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: kms-sfdc-api-service
  namespace: kms-sfdc
spec:
  selector:
    app: kms-sfdc-api
  ports:
  - port: 80
    targetPort: 8008
    protocol: TCP
  type: ClusterIP
```

**Ingress** (`k8s/ingress.yaml`):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kms-sfdc-ingress
  namespace: kms-sfdc
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: kms-sfdc-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kms-sfdc-api-service
            port:
              number: 80
```

#### 2. Deploy to Kubernetes

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n kms-sfdc
kubectl get services -n kms-sfdc

# View logs
kubectl logs -f deployment/kms-sfdc-api -n kms-sfdc

# Scale deployment
kubectl scale deployment kms-sfdc-api --replicas=5 -n kms-sfdc
```

## 🔒 Security Configuration

### 1. API Security

**Authentication Middleware** (`src/security/auth.py`):
```python
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            os.getenv("JWT_SECRET_KEY"), 
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Apply to protected endpoints
@app.post("/admin/rebuild-index")
async def rebuild_index(user=Depends(verify_token)):
    # Admin operation
    pass
```

**Rate Limiting** (`src/security/rate_limit.py`):
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply rate limits
@app.post("/search")
@limiter.limit("100/minute")
async def search_cases(request: Request, search_request: SearchRequest):
    # Search operation
    pass
```

### 2. Environment Security

**Environment Variables** (`.env.production`):
```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=your-super-secret-key-here

# Database
DATABASE_URL=postgresql://user:pass@localhost/kmssfdc

# Salesforce (use secrets management)
SFDC_USERNAME=${VAULT_SFDC_USERNAME}
SFDC_PASSWORD=${VAULT_SFDC_PASSWORD}
SFDC_SECURITY_TOKEN=${VAULT_SFDC_TOKEN}

# Security
JWT_SECRET_KEY=${VAULT_JWT_SECRET}
API_KEY_HASH=${VAULT_API_KEY_HASH}

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_AUTH_TOKEN=${VAULT_METRICS_TOKEN}
```

### 3. Network Security

**Firewall Rules**:
```bash
# Allow SSH (restrict to management IPs)
sudo ufw allow from 10.0.0.0/8 to any port 22

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow monitoring (restrict to monitoring network)
sudo ufw allow from 10.1.0.0/16 to any port 9090
sudo ufw allow from 10.1.0.0/16 to any port 3000

# Deny all other traffic
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

## 📊 Monitoring Setup

### 1. Prometheus Configuration

**Prometheus Config** (`monitoring/prometheus.yml`):
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alertmanager:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'kms-sfdc-api'
    static_configs:
      - targets: ['localhost:8008']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
      
  - job_name: 'nginx'
    static_configs:
      - targets: ['localhost:9113']
```

**Alert Rules** (`monitoring/alert_rules.yml`):
```yaml
groups:
- name: kms-sfdc-alerts
  rules:
  - alert: APIHighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "API error rate is {{ $value }} errors/sec"
      
  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is above 90%"
      
  - alert: VectorDBNotReady
    expr: vector_db_ready == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Vector database not ready"
      description: "Vector database is not ready to serve requests"
```

### 2. Grafana Dashboards

**API Dashboard** (`monitoring/grafana/dashboards/api-dashboard.json`):
```json
{
  "dashboard": {
    "id": null,
    "title": "KMS-SFDC API Dashboard",
    "tags": ["kms-sfdc"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph", 
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Vector DB Stats",
        "type": "stat",
        "targets": [
          {
            "expr": "vector_db_total_vectors",
            "legendFormat": "Total Vectors"
          }
        ]
      }
    ]
  }
}
```

### 3. Log Management

**Fluentd Configuration** (`monitoring/fluentd.conf`):
```xml
<source>
  @type tail
  path /var/log/kms-sfdc/*.log
  pos_file /var/log/fluentd/kms-sfdc.log.pos
  tag kms-sfdc.*
  format multiline
  format_firstline /^\d{4}-\d{2}-\d{2}/
  format1 /^(?<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (?<logger>\w+) - (?<level>\w+) - (?<message>.*)/
</source>

<filter kms-sfdc.**>
  @type parser
  key_name message
  <parse>
    @type json
  </parse>
</filter>

<match kms-sfdc.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name kms-sfdc
  type_name _doc
  logstash_format true
  logstash_prefix kms-sfdc
</match>
```

## 🔄 Backup and Recovery

### 1. Automated Backup Script

**Backup Script** (`scripts/backup.sh`):
```bash
#!/bin/bash

BACKUP_DIR="/var/lib/kms-sfdc/backups"
DATA_DIR="/var/lib/kms-sfdc/data"
S3_BUCKET="kms-sfdc-backups"
RETENTION_DAYS=30

# Create timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="kms-sfdc-backup-$TIMESTAMP"

echo "Starting backup: $BACKUP_NAME"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup vector database files
cp "$DATA_DIR/faiss_index.bin" "$BACKUP_DIR/$BACKUP_NAME/"
cp "$DATA_DIR/case_metadata.json" "$BACKUP_DIR/$BACKUP_NAME/"
cp "$DATA_DIR/sync_state.json" "$BACKUP_DIR/$BACKUP_NAME/"
cp "$DATA_DIR/scheduler_config.json" "$BACKUP_DIR/$BACKUP_NAME/"

# Create archive
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

# Upload to S3 (if configured)
if [ ! -z "$S3_BUCKET" ]; then
    aws s3 cp "$BACKUP_NAME.tar.gz" "s3://$S3_BUCKET/backups/"
fi

# Cleanup old backups
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_NAME.tar.gz"
```

### 2. Recovery Procedures

**Recovery Script** (`scripts/recover.sh`):
```bash
#!/bin/bash

BACKUP_FILE=$1
DATA_DIR="/var/lib/kms-sfdc/data"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    exit 1
fi

echo "Starting recovery from: $BACKUP_FILE"

# Stop services
sudo systemctl stop kms-sfdc-api
sudo systemctl stop kms-sfdc-scheduler

# Backup current data
mv "$DATA_DIR" "${DATA_DIR}.backup.$(date +%s)"
mkdir -p "$DATA_DIR"

# Extract backup
tar -xzf "$BACKUP_FILE" -C /tmp/
cp /tmp/kms-sfdc-backup-*/* "$DATA_DIR/"

# Set permissions
chown -R kms-sfdc:kms-sfdc "$DATA_DIR"

# Start services
sudo systemctl start kms-sfdc-api
sudo systemctl start kms-sfdc-scheduler

echo "Recovery completed"
```

## 🔧 Maintenance Procedures

### 1. Regular Maintenance Tasks

**Weekly Maintenance** (`scripts/weekly_maintenance.sh`):
```bash
#!/bin/bash

echo "Starting weekly maintenance..."

# Update system packages
sudo apt update && sudo apt upgrade -y

# Cleanup logs older than 30 days
find /var/log/kms-sfdc -name "*.log*" -mtime +30 -delete

# Vacuum vector database (if applicable)
# This would depend on specific database implementation

# Restart services for memory cleanup
sudo systemctl restart kms-sfdc-api
sudo systemctl restart kms-sfdc-scheduler

# Run health checks
curl -f http://localhost:8008/health || echo "Health check failed"

echo "Weekly maintenance completed"
```

### 2. Performance Optimization

**Index Optimization** (`scripts/optimize_index.py`):
```python
#!/usr/bin/env python3
"""Optimize vector database index for better performance."""

import sys
import os
sys.path.append('/opt/kms-sfdc')

from src.vectorization import VectorDatabase
from src.utils.config import config

def optimize_index():
    """Optimize vector database index."""
    print("Starting index optimization...")
    
    # Load current index
    vector_db = VectorDatabase()
    vector_db.load_index()
    
    print(f"Current index stats: {vector_db.get_stats()}")
    
    # Perform optimization (example: rebuild with optimized parameters)
    if vector_db.index.ntotal > 50000:
        # Use HNSW index for large datasets
        print("Converting to HNSW index for better performance...")
        # Implementation would depend on specific optimization needs
    
    # Save optimized index
    vector_db.save_index()
    
    print("Index optimization completed")

if __name__ == "__main__":
    optimize_index()
```

## 📋 Deployment Checklist

### Pre-deployment Checklist

- [ ] System requirements verified
- [ ] SSL certificates obtained and configured
- [ ] Environment variables and secrets configured
- [ ] Firewall rules applied
- [ ] Monitoring and alerting configured
- [ ] Backup procedures tested
- [ ] Load testing completed
- [ ] Security scan performed
- [ ] Documentation updated

### Post-deployment Checklist

- [ ] All services started successfully
- [ ] Health checks passing
- [ ] API endpoints responding correctly
- [ ] Admin UI accessible
- [ ] Scheduler running and jobs configured
- [ ] Monitoring dashboards showing data
- [ ] Log aggregation working
- [ ] Backup jobs scheduled and tested
- [ ] Performance metrics within targets
- [ ] Security measures verified

### Go-live Checklist

- [ ] DNS updated to point to production
- [ ] Load balancer configured and tested
- [ ] CDN configured (if applicable)
- [ ] Monitoring alerts enabled
- [ ] On-call procedures established
- [ ] Rollback procedures tested
- [ ] Team training completed
- [ ] Documentation published
- [ ] Support contacts updated
- [ ] Post-launch monitoring scheduled

This comprehensive deployment guide ensures a successful production deployment of the KMS-SFDC Vector Database system with proper security, monitoring, and maintenance procedures.