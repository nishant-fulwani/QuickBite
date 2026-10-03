# Use Python 3.12 which is fully compatible with psycopg2
FROM python:3.12-slim

# Install system dependencies required for PostgreSQL
RUN apt-get update && \
    apt-get install -y gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for the Flask server
EXPOSE 5000

# Tell Flask to run on 0.0.0.0 so it is accessible outside the container
ENV FLASK_APP=app.py
CMD ["flask", "run", "--host=0.0.0.0"]