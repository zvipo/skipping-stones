FROM python:3.11-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything to the container
COPY . /app/

# Expose the port
EXPOSE 5000

# Run the app using gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"] 