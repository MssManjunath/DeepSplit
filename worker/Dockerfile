FROM xserrat/facebook-demucs:latest

# Install Redis and MinIO Python clients
RUN pip install redis minio requests

# Copy your worker code into the container
COPY worker-server.py /worker-server.py

# Set the working directory
WORKDIR /app

# Define the entrypoint to run the worker
ENTRYPOINT ["python3", "/worker-server.py"]
