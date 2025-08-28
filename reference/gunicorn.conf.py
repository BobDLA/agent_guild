# Gunicorn Configuration for Subagent Guild Production

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.environ.get("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout
timeout = 30
keepalive = 2

# Logging
accesslog = "./logs/access.log"
errorlog = "./logs/error.log"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "agent-guild"

# Server mechanics
daemon = False
pidfile = "./logs/gunicorn.pid"
user = None
group = None
tmp_upload_dir = "./data/temp"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
preload_app = True
worker_tmp_dir = "/dev/shm"

# SSL (if terminating SSL at application level)
# keyfile = "/path/to/ssl/key.pem"
# certfile = "/path/to/ssl/cert.pem"

# Hooks
def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker aborted (pid: %s)", worker.pid)