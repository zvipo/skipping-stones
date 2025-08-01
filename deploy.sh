#!/bin/bash

# Build the Docker image
echo "Building Docker image..."
docker build -t skippingstones .

# Run the container
echo "Starting container..."
docker run -d \
  --name skippingstones \
  -p 5000:5000 \
  skippingstones

echo "Application is running on http://localhost:5000"
echo "To stop the container: docker stop skippingstones"
echo "To remove the container: docker rm skippingstones" 