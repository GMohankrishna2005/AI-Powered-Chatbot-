# Production WSGI Server Configuration

This project uses **Gunicorn** as the production WSGI server.

## Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Production Server

### Basic usage (single worker):
```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

### Recommended production setup (4 workers):
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class sync --timeout 30 --access-logfile - wsgi:app
```

### With environment variables:
```bash
set FLASK_ENV=production
gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
```

## Advanced Configuration

Create a `gunicorn_config.py` for more control:

```python
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
accesslog = '-'
errorlog = '-'
loglevel = 'info'
```

Then run:
```bash
gunicorn -c gunicorn_config.py wsgi:app
```

## Performance Tips

- **Workers**: Set to `2 × CPU_count + 1` for I/O-bound apps
- **Threads**: For CPU-bound tasks, use `--worker-class gthread --threads 2`
- **Timeout**: Adjust based on request processing time (default: 30s)
- **Max Requests**: Restart workers periodically to prevent memory leaks

## Deployment on Windows

For production on Windows, consider using:
- **IIS with FastCGI** (via wfastcgi)
- **Windows Service** (via NSSM)
- **Docker container**

## Reverse Proxy Setup (Nginx)

```nginx
upstream flaskapp {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://flaskapp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring

Monitor the server with:
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --statsd-host 127.0.0.1:8125 wsgi:app
```
