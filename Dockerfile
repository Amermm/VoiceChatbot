# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Expose port
EXPOSE 8080

# Start the application
CMD ["gunicorn", "-b", "0.0.0.0:8080", "web_ui:app"]
