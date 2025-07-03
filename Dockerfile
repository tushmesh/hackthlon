# Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the working directory
COPY src/ /app/src/
COPY .env /app/.env # Copy your .env file (make sure it's not committed to public repos)

# Command to run the application
CMD ["python", "src/main.py"]