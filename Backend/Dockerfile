# 1. Use a slim Python image to keep the container light
FROM python:3.11-slim

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Install system dependencies for PostGIS/GIS
# These are essential for GeoDjango and H3 processing
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 4. Set working directory
WORKDIR /app
# 5. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the project code
COPY . /app/

# 7. Expose the Django port
EXPOSE 8000

# 8. Start the development server
CMD ["python", "TENeT/manage.py", "runserver", "0.0.0.0:8000"]