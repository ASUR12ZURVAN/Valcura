# Valcura Patient Automation System - Production Deployment Guide

## Overview

This system provides automated patient communication through WhatsApp, integrated with Google Sheets for patient management and a template-based workflow engine for personalized messaging.

## Required API Keys and Services

### 1. Google Sheets API

**Purpose**: Read patient data and update patient status in Google Sheets

**Required Credentials**:
- `GOOGLE_SHEETS_SPREADSHEET_ID`: Your Google Sheet ID
- `GOOGLE_SERVICE_ACCOUNT_FILE`: Path to service account JSON file OR
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Service account JSON as environment variable
- `GOOGLE_SHEETS_PATIENT_SHEET`: Name of patient status sheet (default: "Patient Status")

**Setup Instructions**:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API and Google Drive API
4. Create a service account:
   - Go to IAM & Admin → Service Accounts
   - Click "Create Service Account"
   - Give it a name (e.g., "valcura-automation")
   - Click "Create and Continue"
5. Grant service account access:
   - Go to your Google Sheet
   - Click "Share"
   - Add the service account email with "Editor" permissions
6. Create service account key:
   - Go to Service Accounts → Click your service account
   - Go to "Keys" tab → "Add Key" → "Create New Key"
   - Choose JSON format and download
7. Save the JSON file securely (never commit to git)

**Environment Variables**:
```bash
GOOGLE_SHEETS_SPREADSHEET_ID=1PLPAP2W6iZHqo47KG60sqNmv1EHwE4PG4Eh1wUYyPdY
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/your/service-account.json
# OR
GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "...", ...}'
GOOGLE_SHEETS_PATIENT_SHEET=Patient Status
```

### 2. WhatsApp Business API

**Purpose**: Send automated WhatsApp messages to patients

**Required Credentials**:
- `WHATSAPP_ACCESS_TOKEN`: Access token from Meta Business Suite
- `WHATSAPP_PHONE_NUMBER_ID`: Your WhatsApp Business phone number ID
- `WHATSAPP_API_VERSION`: API version (default: "v18.0")

**Setup Instructions**:

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Create a Meta Business account if you don't have one
3. Create a WhatsApp Business App:
   - Go to Business Settings → Apps → "Create App"
   - Select "Business" type
   - Choose "WhatsApp" product
4. Configure WhatsApp:
   - Add your WhatsApp Business phone number
   - Verify phone number
   - Get Phone Number ID from WhatsApp settings
5. Generate Access Token:
   - Go to App Settings → WhatsApp → API Configuration
   - Generate temporary access token (for testing) or permanent token (for production)
6. Submit message templates to Meta for approval:
   - Use your template names from the CSV file
   - Submit each template for Meta approval

**Environment Variables**:
```bash
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_API_VERSION=v18.0
```

### 3. Django Configuration

**Required Settings**:
- `SECRET_KEY`: Django secret key for cryptographic signing
- `DEBUG`: Set to False in production
- `ALLOWED_HOSTS`: Your domain names
- Database configuration (PostgreSQL recommended for production)

**Environment Variables**:
```bash
SECRET_KEY=your_django_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### 4. Database Configuration (PostgreSQL - Recommended for Production)

**Required Credentials**:
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port (default: 5432)

**Environment Variables**:
```bash
DB_NAME=valcura_production
DB_USER=valcura_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Cache Configuration (Redis - Recommended for Production)

**Required Credentials**:
- `REDIS_URL`: Redis connection URL or individual Redis settings

**Environment Variables**:
```bash
REDIS_URL=redis://localhost:6379/1
# OR
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1
```

## Complete .env File Template

```bash
# Django Settings
SECRET_KEY=your_django_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL)
DB_NAME=valcura_production
DB_USER=valcura_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Cache (Redis)
REDIS_URL=redis://localhost:6379/1

# Google Sheets API
GOOGLE_SHEETS_SPREADSHEET_ID=1PLPAP2W6iZHqo47KG60sqNmv1EHwE4PG4Eh1wUYyPdY
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
GOOGLE_SHEETS_PATIENT_SHEET=Patient Status

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
WHATSAPP_API_VERSION=v18.0

# Optional: Google Sheets Webhook (alternative to service account)
# GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
```

## Google Sheets Structure

Your Google Sheet should have a "Patient Status" sheet with the following columns:

### Required Columns:
- `phone_number` / `Phone Number`: Patient's phone number
- `patient_name` / `Patient Name`: Patient's name
- `status` / `Status`: Current patient status (new, inquiry, consultation_scheduled, etc.)
- `treatment` / `Treatment`: Type of treatment (Root Canal Treatment, Implants, etc.)
- `appointment_date` / `Appointment Date`: Scheduled appointment date (YYYY-MM-DD)
- `appointment_time` / `Appointment Time`: Scheduled appointment time
- `last_contact_date` / `Last Contact Date`: Date of last contact (YYYY-MM-DD)

### Optional Columns:
- `objection` / `Objection`: Patient's objection or concern
- `notes` / `Notes`: Additional notes about the patient
- `library` / `Library`: Current workflow library
- `clinic_name` / `Clinic Name`: Your clinic name
- `doctor_name` / `Doctor Name`: Doctor's name

## Installation Steps

### 1. Clone and Setup Repository

```bash
git clone <your-repository-url>
cd Valcura/Valcura_backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Add these packages to your `requirements.txt`:
```
django>=4.2.0
gspread>=5.7.0
google-auth>=2.17.0
requests>=2.31.0
python-decouple>=3.8
psycopg2-binary>=2.9.0
redis>=4.5.0
celery>=5.3.0
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 5. Database Setup

```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Import templates from CSV
python manage.py import_templates --csv-file "../Meta Templates - Sheet1.csv"
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Test the Setup

```bash
# Run development server
python manage.py runserver

# Test automation
python manage.py run_automation --type=followups
```

## Deployment Options

### Option 1: Traditional VPS/Server Deployment

#### Server Requirements:
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Nginx (as reverse proxy)

#### Deployment Steps:

1. **Server Setup**:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv postgresql postgresql-contrib redis-server nginx -y

# Install project dependencies
cd /var/www/valcura
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure PostgreSQL**:
```bash
sudo -u postgres psql
CREATE DATABASE valcura_production;
CREATE USER valcura_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE valcura_production TO valcura_user;
\q
```

3. **Configure Nginx**:
```nginx
# /etc/nginx/sites-available/valcura
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /var/www/valcura/static/;
    }
}
```

4. **Setup Systemd Service**:
```ini
# /etc/systemd/system/valcura.service
[Unit]
Description=Valcura Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/valcura
Environment="PATH=/var/www/valcura/venv/bin"
ExecStart=/var/www/valcura/venv/bin/gunicorn Valcura_backend.wsgi:application --workers 3 --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

5. **Setup Celery for Background Tasks**:
```ini
# /etc/systemd/system/valcura-celery.service
[Unit]
Description=Valcura Celery Worker
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/valcura
Environment="PATH=/var/www/valcura/venv/bin"
ExecStart=/var/www/valcura/venv/bin/celery -A Valcura_backend worker --loglevel=info

[Install]
WantedBy=multi-user.target
```

6. **Setup Cron Jobs for Automation**:
```bash
# Edit crontab
crontab -e

# Add these lines:
# Run follow-ups every 2 hours during business hours
0 9,11,13,15,17 * * * cd /var/www/valcura && /var/www/valcura/venv/bin/python manage.py run_automation --type=followups

# Run reminders at 9 AM daily
0 9 * * * cd /var/www/valcura && /var/www/valcura/venv/bin/python manage.py run_automation --type=reminders

# Sync workflow state every 6 hours
0 */6 * * * cd /var/www/valcura && /var/www/valcura/venv/bin/python manage.py run_automation --type=sync
```

### Option 2: Docker Deployment

#### Dockerfile:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

EXPOSE 8000

CMD ["gunicorn", "Valcura_backend.wsgi:application", "--workers", "3", "--bind", "0.0.0.0:8000"]
```

#### docker-compose.yml:
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: valcura_production
      POSTGRES_USER: valcura_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis
    volumes:
      - .:/app
      - ./service-account.json:/app/service-account.json

  celery:
    build: .
    command: celery -A Valcura_backend worker --loglevel=info
    environment:
      - DEBUG=False
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

#### Deployment Commands:
```bash
# Build and start containers
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Import templates
docker-compose exec web python manage.py import_templates --csv-file "../Meta Templates - Sheet1.csv"

# Run automation manually
docker-compose exec web python manage.py run_automation --type=all
```

### Option 3: Cloud Platform Deployment (AWS/Heroku)

#### Heroku Deployment:

1. **Create Procfile**:
```
web: gunicorn Valcura_backend.wsgi:application --workers 3
worker: celery -A Valcura_backend worker --loglevel=info
```

2. **Create runtime.txt**:
```
python-3.11.0
```

3. **Deploy Commands**:
```bash
# Login to Heroku
heroku login

# Create app
heroku create valcura-production

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Add Redis
heroku addons:create heroku-redis:mini

# Set environment variables
heroku config:set SECRET_KEY=your_secret_key
heroku config:set DEBUG=False
heroku config:set GOOGLE_SHEETS_SPREADSHEET_ID=your_sheet_id
heroku config:set WHATSAPP_ACCESS_TOKEN=your_token
heroku config:set WHATSAPP_PHONE_NUMBER_ID=your_phone_id

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate

# Import templates
heroku run python manage.py import_templates --csv-file "Meta Templates - Sheet1.csv"

# Setup scheduler add-on for automation
heroku addons:create heroku-scheduler:standard
```

#### AWS Elastic Beanstalk:

1. **Create application and environment**
2. **Configure environment variables in EB console**
3. **Deploy using EB CLI**:
```bash
eb init valcura-production
eb create production-environment
```

### Option 4: Render.com Deployment (Recommended)

Render is a modern cloud platform that simplifies deployment with built-in PostgreSQL, Redis, and cron jobs.

#### Prerequisites:
- GitHub repository with your code
- Render account (free tier available)
- All API keys configured

#### Step 1: Prepare Your Repository

1. **Create `render.yaml`** in your project root:
```yaml
services:
  - type: web
    name: valcura-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn Valcura_backend.wsgi:application --workers 3 --bind 0.0.0.0:$PORT
    envVars:
      - key: DJANGO_SETTINGS_MODULE
        value: Valcura_backend.settings
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: false
      - key: PYTHON_VERSION
        value: 3.11.0
    disk:
      name: data
      mountPath: /opt/render/project/data
      sizeGB: 1

databases:
  - name: valcura-db
    databaseName: valcura_production
    user: valcura_user

  - name: valcura-redis
    engine: redis
```

2. **Create `Procfile`** in project root:
```
web: gunicorn Valcura_backend.wsgi:application --workers 3 --bind 0.0.0.0:$PORT
```

3. **Create `.python-version`**:
```
3.11
```

4. **Update `requirements.txt`** to include all dependencies:
```
django>=4.2.0
gspread>=5.7.0
google-auth>=2.17.0
requests>=2.31.0
python-decouple>=3.8
psycopg2-binary>=2.9.0
redis>=4.5.0
celery>=5.3.0
gunicorn>=21.2.0
openpyxl>=3.1.0
```

#### Step 2: Deploy to Render

1. **Connect GitHub to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `Valcura` repository

2. **Configure Web Service**:
   - **Name**: valcura-backend
   - **Region**: Choose nearest region (e.g., Oregon)
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn Valcura_backend.wsgi:application --workers 3 --bind 0.0.0.0:$PORT`

3. **Add Environment Variables**:
   ```
   DJANGO_SETTINGS_MODULE=Valcura_backend.settings
   SECRET_KEY=your_django_secret_key_here
   DEBUG=False
   ALLOWED_HOSTS=your-app-name.onrender.com
   
   # Database (Render provides these automatically)
   DATABASE_URL=render provides this
   REDIS_URL=render provides this
   
   # Google Sheets API
   GOOGLE_SHEETS_SPREADSHEET_ID=your_sheet_id
   GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
   
   # WhatsApp Business API
   WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
   WHATSAPP_PHONE_NUMBER_ID=your_phone_id
   WHATSAPP_API_VERSION=v18.0
   ```

4. **Create PostgreSQL Database**:
   - Click "New +" → "PostgreSQL"
   - **Name**: valcura-db
   - **Database**: valcura_production
   - **User**: valcura_user
   - **Region**: Same as web service
   - **Plan**: Free (dev) or paid (production)

5. **Create Redis Instance**:
   - Click "New +" → "Redis"
   - **Name**: valcura-redis
   - **Region**: Same as web service
   - **Plan**: Free (dev) or paid (production)

6. **Deploy**:
   - Click "Create Web Service"
   - Render will automatically build and deploy
   - Monitor the deployment logs

#### Step 3: Post-Deployment Setup

1. **Run Database Migrations**:
   - Go to your web service in Render
   - Click "Shell" tab
   - Run:
   ```bash
   python manage.py migrate
   ```

2. **Import Templates**:
   ```bash
   python manage.py import_templates --csv-file "Meta Templates - Sheet1.csv"
   ```

3. **Import Excel Data** (if using database source):
   ```bash
   python manage.py import_excel
   ```

4. **Create Superuser**:
   ```bash
   python manage.py createsuperuser
   ```

#### Step 4: Setup Cron Jobs for Automation

Render has built-in cron job support:

1. **Create Cron Job**:
   - Click "New +" → "Cron Job"
   - **Name**: patient-followups
   - **Command**: `python manage.py run_automation --type=followups --data-source=database`
   - **Schedule**: `0 */2 * * *` (every 2 hours)
   - **Region**: Same as web service

2. **Create Additional Cron Jobs**:
   - **Appointment Reminders**:
     - Name: appointment-reminders
     - Command: `python manage.py run_automation --type=reminders --data-source=database`
     - Schedule: `0 9 * * *` (daily at 9 AM)
   
   - **Workflow Sync**:
     - Name: workflow-sync
     - Command: `python manage.py run_automation --type=sync --data-source=database`
     - Schedule: `0 */6 * * *` (every 6 hours)

#### Step 5: Configure Django Settings for Render

Update your `settings.py` to work with Render:

```python
import os
import dj_database_url
from decouple import config

# Database
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True
        )
    }

# Redis Cache
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Allowed Hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['*']  # Only for development
```

#### Step 6: Monitor and Scale

1. **Monitoring**:
   - Render provides built-in metrics (CPU, memory, response time)
   - View logs in the "Logs" tab
   - Set up alerts in Render dashboard

2. **Scaling**:
   - **Vertical Scaling**: Increase instance size in service settings
   - **Horizontal Scaling**: Add more instances (paid plans only)
   - **Database Scaling**: Upgrade PostgreSQL plan for higher limits

3. **Backup**:
   - Render automatically backs up PostgreSQL databases daily
   - Manual backups available in database settings

#### Render-Specific Considerations:

1. **File Storage**:
   - Render's file system is ephemeral
   - Use Render Disk for persistent storage
   - Store Excel files in external storage (S3, Google Drive)

2. **Excel File Handling**:
   - Upload Excel file to Google Drive
   - Use Google Drive API to read the file
   - Or use Render Disk for persistent storage

3. **Service Account JSON**:
   - Store service account JSON as environment variable
   - Use `GOOGLE_SERVICE_ACCOUNT_JSON` instead of file path
   - Never commit secrets to GitHub

4. **WhatsApp Webhooks**:
   - Render provides HTTPS automatically
   - Configure webhook URL in Meta Business Suite
   - Format: `https://your-app-name.onrender.com/webhooks/whatsapp/`

5. **Celery Workers** (Optional):
   - For background tasks, create a separate worker service
   - Use Render's "Worker" service type
   - Configure with same environment variables

#### Cost Estimation (Render):

**Free Tier**:
- Web Service: $0/month (limited resources)
- PostgreSQL: $0/month (90MB storage)
- Redis: $0/month (25MB storage)
- Cron Jobs: $0/month (limited)

**Production Tier**:
- Web Service: $7/month (512MB RAM)
- PostgreSQL: $7/month (1GB storage)
- Redis: $7/month (25MB storage)
- Cron Jobs: $7/month
- **Total**: ~$28/month

**High-Performance Tier**:
- Web Service: $25/month (2GB RAM)
- PostgreSQL: $20/month (10GB storage)
- Redis: $20/month (256MB storage)
- Cron Jobs: $7/month
- **Total**: ~$72/month

#### Troubleshooting Render Deployment:

1. **Build Failures**:
   - Check build logs in Render dashboard
   - Ensure all dependencies are in requirements.txt
   - Verify Python version compatibility

2. **Database Connection Issues**:
   - Ensure DATABASE_URL is set correctly
   - Check database is in same region as web service
   - Verify database is not in "Suspended" state

3. **Cron Job Failures**:
   - Check cron job logs
   - Verify command syntax
   - Ensure environment variables are set

4. **Memory Issues**:
   - Upgrade to larger instance size
   - Optimize database queries
   - Implement caching

#### Render vs Other Platforms:

**Advantages of Render**:
- Zero configuration deployment
- Built-in PostgreSQL and Redis
- Automatic SSL certificates
- Easy cron job setup
- Simple scaling
- Good free tier for development

**When to Choose Render**:
- Small to medium applications
- Quick deployment needed
- Limited DevOps resources
- Want managed database and cache

**When to Consider Other Platforms**:
- Very large scale applications
- Complex infrastructure requirements
- Need specific cloud provider features
- Cost optimization at scale

## Security Considerations

### 1. API Key Security
- Never commit `.env` files or service account JSON files to version control
- Use environment variables for all sensitive data
- Rotate access tokens regularly
- Use different tokens for development and production

### 2. Google Sheets Security
- Limit service account permissions to only necessary scopes
- Share Google Sheets only with required service account email
- Enable audit logging for Google Cloud project
- Regularly review service account access

### 3. WhatsApp API Security
- Use IP whitelisting if available
- Monitor API usage for unusual activity
- Implement rate limiting to prevent abuse
- Keep access tokens secure and rotate regularly

### 4. Database Security
- Use strong passwords for database users
- Enable SSL/TLS for database connections
- Regular database backups
- Limit database user permissions

### 5. Application Security
- Enable HTTPS in production (use Let's Encrypt for free SSL)
- Implement CSRF protection
- Use Django's built-in security middleware
- Regular security updates for dependencies
- Implement logging and monitoring

## Monitoring and Maintenance

### 1. Application Monitoring
- Set up error tracking (Sentry, Rollbar)
- Monitor application performance (New Relic, Datadog)
- Log automation runs and message delivery status
- Set up alerts for failures

### 2. Database Maintenance
- Regular database backups
- Index optimization
- Query performance monitoring
- Storage monitoring

### 3. WhatsApp API Monitoring
- Monitor message delivery rates
- Track template approval status
- Monitor API quota usage
- Set up alerts for API failures

### 4. Google Sheets Monitoring
- Monitor API rate limits
- Track sync status
- Validate data integrity
- Monitor for unauthorized access

## Troubleshooting

### Common Issues:

1. **Google Sheets Connection Failed**:
   - Verify service account has editor access to the sheet
   - Check that spreadsheet ID is correct
   - Ensure service account JSON file path is correct
   - Verify API quotas haven't been exceeded

2. **WhatsApp Messages Not Sending**:
   - Verify access token is valid and not expired
   - Check phone number ID is correct
   - Ensure templates are approved by Meta
   - Verify phone number format (include country code)

3. **Automation Not Running**:
   - Check cron job configuration
   - Verify system service is running
   - Check application logs for errors
   - Ensure environment variables are set correctly

4. **Database Connection Issues**:
   - Verify database credentials
   - Check database server is running
   - Ensure firewall allows connection
   - Verify database exists and user has permissions

## Scaling Considerations

### 1. Horizontal Scaling
- Use load balancer for multiple web servers
- Implement session storage in Redis
- Use Celery with multiple workers for background tasks

### 2. Database Scaling
- Use read replicas for read-heavy operations
- Implement connection pooling
- Consider database sharding for large datasets

### 3. Cache Scaling
- Use Redis Cluster for distributed caching
- Implement cache warming strategies
- Monitor cache hit rates

### 4. API Rate Limiting
- Implement exponential backoff for API calls
- Use queue systems for high-volume operations
- Consider API caching where appropriate

## Backup and Recovery

### 1. Database Backups
```bash
# Daily backup
pg_dump -U valcura_user -h localhost valcura_production > backup_$(date +%Y%m%d).sql

# Restore
psql -U valcura_user -h localhost valcura_production < backup_20240101.sql
```

### 2. Google Sheets Backup
- Enable Google Drive version history
- Regular exports to CSV
- Consider automated backup scripts

### 3. Configuration Backup
- Backup .env files securely
- Document all API key locations
- Maintain configuration in version control (without secrets)

## Support and Maintenance

### Regular Tasks:
- Weekly: Review automation logs and error rates
- Monthly: Review and rotate API keys
- Quarterly: Review and update dependencies
- Annually: Security audit and compliance review

### Emergency Contacts:
- Meta Business Support: For WhatsApp API issues
- Google Cloud Support: For Sheets API issues
- System administrator: For server infrastructure issues

## Cost Estimation

### Development Environment:
- VPS: $5-20/month
- Database: Free (SQLite) or $15/month (PostgreSQL)
- WhatsApp API: Free tier available
- Google Sheets API: Free tier sufficient for most use cases

### Production Environment:
- VPS/Cloud: $20-100/month depending on scale
- Database: $15-50/month (managed PostgreSQL)
- Redis: $10-30/month (managed Redis)
- WhatsApp API: Pay per conversation (varies by region)
- Monitoring: $10-50/month depending on tools

## Additional Resources

- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp/business-api/)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

## Contact and Support

For issues specific to this implementation:
- Check application logs first
- Review this documentation
- Consult service-specific documentation
- Contact system administrator for infrastructure issues
