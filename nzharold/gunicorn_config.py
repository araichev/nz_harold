workers = 4
threads = 4
worker_tmp_dir = "/dev/shm"

bind = "127.0.0.1:5020"
umask = 0o007
reload = False
forwarded_allow_ips = "*"

# logging
accesslog = "-"
errorlog = "-"

max_requests = 500
max_requests_jitter = 50
