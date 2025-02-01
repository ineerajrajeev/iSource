# Dockerfile for the Flask app
# ==============================

# Use official Python slim image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the port where Flask runs
EXPOSE 5000

# By default run the application
CMD ["python", "app.py"]
