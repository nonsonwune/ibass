# Gunicorn configuration file
bind = "0.0.0.0:10000"
workers = 3
timeout = 120
limit_request_line = 0
limit_request_fields = 1000
limit_request_field_size = 0 