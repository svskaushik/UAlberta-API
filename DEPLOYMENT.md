# Production Deployment Guide

## Overview
This guide shows how to deploy the Multi-University Data API to production using Coolify or similar platforms.

## Prerequisites
- PostgreSQL database (managed service recommended)
- Container hosting platform (Coolify, Railway, Render, etc.)
- Domain name (optional)

## Environment Variables

Set these environment variables in your production environment:

```bash
# Database
DATABASE_URL=postgresql+psycopg2://username:password@host:port/database

# Application
DEBUG=False
API_HOST=0.0.0.0
API_PORT=8000

# Scraping
SCRAPING_DELAY=2
SCRAPING_TIMEOUT=30

# University-specific
UALBERTA_BASE_URL=https://apps.ualberta.ca
UALBERTA_EXAM_URL=https://www.ualberta.ca/api/datalist/spreadsheet/1kM0k0LenS9Z9LFH6F9qfbr7lyThRa0phTadDCs_MA-c/Sheet1
```

## Deployment Steps

### 1. Set up PostgreSQL Database

**On Coolify:**
1. Go to your Coolify dashboard
2. Create a new PostgreSQL service
3. Note the connection details
4. Run the schema creation:
   ```sql
   -- Run the contents of database/schema.sql
   ```

### 2. Deploy the Application

**Using Docker (Coolify/Railway/Render):**

1. **Build and push image:**
   ```bash
   docker build -t university-api .
   docker tag university-api your-registry/university-api:latest
   docker push your-registry/university-api:latest
   ```

2. **Deploy on Coolify:**
   - Create new application
   - Use Docker image: `your-registry/university-api:latest`
   - Set environment variables
   - Configure port: 8000
   - Deploy

3. **Deploy on Railway:**
   ```bash
   railway login
   railway new
   railway add
   railway up
   ```

### 3. Initialize Database

After deployment, run the migration script to set up initial data:

```bash
# If you have existing JSON data to migrate
python migrate_data.py

# Or start fresh and scrape data
curl -X POST https://your-domain.com/api/ualberta/scrape_all
```

### 4. Set up Monitoring

**Health Check Endpoint:**
- URL: `https://your-domain.com/`
- Expected: 200 OK with JSON response

**Database Monitoring:**
- Monitor connection pool usage
- Set up alerts for failed queries
- Monitor sync logs via: `/api/ualberta/sync_status`

### 5. Performance Optimization

**Database:**
- Enable connection pooling
- Set up read replicas for high traffic
- Configure backup strategy

**Application:**
- Enable Redis caching (optional)
- Set up CDN for static content
- Configure rate limiting

**Scraping:**
- Schedule regular data updates via cron
- Implement exponential backoff for failed requests
- Monitor university website changes

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple API instances behind a load balancer
- Use shared database and cache
- Implement distributed task queue for scraping

### Vertical Scaling
- Increase memory for larger datasets
- Optimize database queries with indexes
- Use connection pooling

### Multi-University Support
- Add new scrapers to `scrapers/` directory
- Register in `scrapers/registry.py`
- Each university gets isolated data in the database

## Maintenance

### Regular Tasks
1. **Data Updates:** Run scrapers daily/weekly
2. **Database Cleanup:** Archive old sync logs
3. **Monitoring:** Check sync status and error rates
4. **Backups:** Ensure database backups are working

### Updating the Application
1. Build new image with changes
2. Deploy to staging environment
3. Run tests and data validation
4. Deploy to production with zero-downtime strategy

## Security

### API Security
- Implement rate limiting
- Add API authentication for sensitive endpoints
- Use HTTPS in production
- Validate all input data

### Database Security
- Use strong passwords
- Enable SSL connections
- Restrict network access
- Regular security updates

## Cost Optimization

### Database
- Use managed PostgreSQL service
- Optimize queries to reduce CPU usage
- Archive old data regularly

### Hosting
- Use auto-scaling based on traffic
- Implement caching to reduce database load
- Monitor resource usage

## Troubleshooting

### Common Issues

**Database Connection Errors:**
- Check DATABASE_URL format
- Verify network connectivity
- Check database service status

**Scraping Failures:**
- Check university website changes
- Verify network access to target sites
- Review sync logs for error details

**High Memory Usage:**
- Optimize database queries
- Implement pagination for large datasets
- Add response caching

### Logs and Monitoring

**Application Logs:**
- Check uvicorn/FastAPI logs
- Monitor scraping success rates
- Track API response times

**Database Logs:**
- Monitor slow queries
- Check connection pool status
- Review sync_logs table for patterns

## API Documentation

Once deployed, API documentation is available at:
- Swagger UI: `https://your-domain.com/docs`
- ReDoc: `https://your-domain.com/redoc`
