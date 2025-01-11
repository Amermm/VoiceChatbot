# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy application files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask will run on
EXPOSE 8080

# Command to start the Flask app
CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "web_ui:app", "-b", "0.0.0.0:8080", "--timeout", "120"]
