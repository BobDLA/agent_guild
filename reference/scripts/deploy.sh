#!/bin/bash

# Subagent Guild - Production Deployment Script

set -e

echo "🚀 Starting Subagent Guild deployment..."

# Configuration
APP_DIR="/opt/agent-guild"
SERVICE_USER="agent-guild"
DOMAIN="your-domain.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "Don't run this script as root!"
    exit 1
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    supervisor \
    curl \
    unzip

# Create application directory
print_status "Setting up application directory..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Clone or update repository
if [ -d "$APP_DIR/.git" ]; then
    print_status "Updating existing repository..."
    cd $APP_DIR
    git pull origin main
else
    print_status "Cloning repository..."
    git clone https://github.com/your-username/agent-guild.git $APP_DIR
    cd $APP_DIR
fi

# Create virtual environment
print_status "Setting up Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements-prod.txt

# Create necessary directories
print_status "Creating application directories..."
mkdir -p data/repositories data/db logs data/temp

# Copy environment configuration
if [ ! -f ".env" ]; then
    print_status "Creating environment configuration..."
    cp .env.template .env
    print_warning "Please edit .env file with your configuration!"
fi

# Initialize database
print_status "Initializing database..."
python -c "
import asyncio
from app.core.database import init_database
asyncio.run(init_database())
"

# Create systemd service files
print_status "Creating systemd services..."

# Main application service
sudo tee /etc/systemd/system/agent-guild.service > /dev/null <<EOF
[Unit]
Description=Subagent Guild Web Application
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Scheduler service
sudo tee /etc/systemd/system/agent-guild-scheduler.service > /dev/null <<EOF
[Unit]
Description=Subagent Guild Background Scheduler
After=network.target agent-guild.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python scripts/scheduler.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable agent-guild agent-guild-scheduler

# Configure Nginx
print_status "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/agent-guild > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias $APP_DIR/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/agent-guild /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Set up SSL certificate
print_status "Setting up SSL certificate..."
print_warning "Make sure DNS is pointing to this server before continuing!"
read -p "Continue with SSL setup? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
fi

# Start services
print_status "Starting services..."
sudo systemctl start agent-guild
sudo systemctl start agent-guild-scheduler

# Configure log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/agent-guild > /dev/null <<EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload agent-guild
    endscript
}
EOF

# Set up monitoring script
print_status "Creating monitoring script..."
tee $APP_DIR/scripts/monitor.sh > /dev/null <<'EOF'
#!/bin/bash

# Simple monitoring script for Agent Guild

check_service() {
    if systemctl is-active --quiet $1; then
        echo "✓ $1 is running"
        return 0
    else
        echo "✗ $1 is not running"
        return 1
    fi
}

check_url() {
    if curl -f -s "$1" > /dev/null; then
        echo "✓ $1 is responding"
        return 0
    else
        echo "✗ $1 is not responding"
        return 1
    fi
}

echo "=== Agent Guild Status Check ==="
echo "Date: $(date)"
echo

# Check services
check_service "agent-guild"
check_service "agent-guild-scheduler"
check_service "nginx"

echo

# Check web endpoints
check_url "http://localhost:8000/health"
check_url "http://localhost:8000/"

echo

# Check disk space
echo "Disk Usage:"
df -h $APP_DIR

echo

# Check recent logs
echo "Recent errors in logs:"
tail -n 10 $APP_DIR/logs/app.log | grep -i error || echo "No recent errors"
EOF

chmod +x $APP_DIR/scripts/monitor.sh

# Add cron job for monitoring
(crontab -l 2>/dev/null; echo "*/5 * * * * $APP_DIR/scripts/monitor.sh >> $APP_DIR/logs/monitor.log 2>&1") | crontab -

print_status "Deployment completed successfully!"
echo
echo "🎉 Subagent Guild is now deployed!"
echo
echo "Next steps:"
echo "1. Edit $APP_DIR/.env with your configuration"
echo "2. Visit https://$DOMAIN to verify the installation"
echo "3. Check service status: sudo systemctl status agent-guild"
echo "4. View logs: tail -f $APP_DIR/logs/app.log"
echo "5. Monitor system: $APP_DIR/scripts/monitor.sh"
echo
print_warning "Don't forget to configure your Claude API key in .env!"