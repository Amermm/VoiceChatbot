# Use an official Python image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    libasound2-dev \
    python3-dev \
    gcc \
    g++ \
    make \
    && apt-get clean

# Copy the application files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app will run on
EXPOSE 5000

# Start the application
CMD ["gunicorn", "web_ui:app", "--timeout", "120", "--workers", "1", "--threads", "4", "--worker-class", "gthread"]
