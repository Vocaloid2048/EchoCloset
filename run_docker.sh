#!/bin/bash

# Build the Docker image
docker build -t echo-closet .

# Run the container with .env mounted
docker run --env-file .env -v $(pwd)/echo_closet_records.json:/app/echo_closet_records.json echo-closet