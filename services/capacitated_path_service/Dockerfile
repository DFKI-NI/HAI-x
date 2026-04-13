FROM python:3.12-slim

# Install system dependencies for GDAL/Proj
#RUN apt-get update && apt-get install -y \
#    binutils \
#    libproj-dev \
#    gdal-bin \
#    libgdal-dev \
#    g++ \
#    && rm -rf /var/lib/apt/lists/*
#
#WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10011"]
