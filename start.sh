gunicorn wsgi:app \
  -b 0.0.0.0:5050 \
  -w 2 -k gthread --threads 4 \
  --timeout 120 \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --access-logformat '%(h)s - %(u)s [%(t)s] "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

