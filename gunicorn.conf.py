import multiprocessing

# Bind and process count
bind = "0.0.0.0:5001"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
worker_class = "gthread"
# worker_connections = 1000 # For async workers

# Performance settings
max_requests = 1000  # Restart workers after handling 1000 requests
max_requests_jitter = 200  # Add jitter to prevent all workers restarting simultaneously
timeout = 120  # Default 30s is often too low for data processing
keepalive = 5  # How long to wait for requests on a keep-alive connection
backlog = 2048

# Logging
errorlog = "/var/log/gunicorn/error.log"
accesslog = "/var/log/gunicorn/access.log"
loglevel = "info" # Capture stdout/stderr from workers
logger_class = "gunicorn.glogging.Logger"
access_log_format = '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
capture_output = True

# Security
limit_request_line = 4094  # Limit the allowed size of an HTTP request line
limit_request_fields = 100  # Limit the number of HTTP headers
limit_request_field_size = 8190  # Limit the allowed size of an HTTP header

# Graceful handling
graceful_timeout = 30  # How long to wait for workers to finish their work during shutdown
preload_app = True  # Load application code before worker processes are forked
