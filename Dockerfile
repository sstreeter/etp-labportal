# Use a Python base image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code to the working directory
COPY . .

# Create a directory for backups inside the container
RUN mkdir -p /tmp/backups

# Set environment variables (for Flask development)
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Expose the port Flask runs on
EXPOSE 8000

# Command to run the application
# This will create tables and then run the Flask app
CMD ["/bin/bash", "-c", "python setup_db.py && python run.py"]