FROM python:3.12
SHELL ["/bin/bash", "-c"]

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Apply Django migrations (sessions + django_plotly_dash bookkeeping) and
# start the application with gunicorn.  For local development use
# `python manage.py runserver 0.0.0.0:8000` instead.
CMD ["bash", "-c", "python manage.py migrate --noinput && gunicorn hai_x.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 300"]
