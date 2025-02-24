# Music Separation as a Service (MSaaS) - Kubernetes

## Overview
This project implements a Kubernetes-based microservices architecture for automatic music separation. The system provides a REST API that allows users to upload MP3 files, processes them using Facebook's Demucs model, and stores the separated audio tracks in a cloud object storage service like MinIO.

## Key Features
- **Kubernetes Cluster Deployment**: Designed and deployed a Kubernetes cluster to host the microservices.
- **REST API**: Built a RESTful service to handle MP3 uploads and initiate processing requests.
- **Worker Nodes**: Developed worker nodes that process MP3 files and separate the tracks using the Demucs model.
- **Redis for Task Queuing**: Implemented Redis to queue tasks for workers efficiently.
- **Cloud Storage Integration**: Used MinIO for storing input MP3 files and separated audio tracks.
- **Scalability & Performance Optimization**: Ensured efficient resource allocation to manage the high memory consumption of the Demucs model.

## Development Process
### 1. Setting Up Kubernetes Cluster
- Used both a local Kubernetes setup and Google Kubernetes Engine (GKE) for deployment.
- Configured Kubernetes manifests for deploying the services.

### 2. Implementing Redis-based Task Queue
- Set up a Redis instance within Kubernetes to manage the queue of MP3 processing requests.
- Used Redis list commands (`lpush`, `blpop`) for job scheduling between REST API and worker nodes.

### 3. Developing the REST API Service
- Built a Flask-based REST API to accept user requests for MP3 uploads and processing.
- Implemented endpoint to retrieve processed audio files from MinIO.

### 4. Implementing the Worker Service
- Created a worker service that listens for new processing jobs in Redis.
- Integrated Demucs to process MP3 files and extract individual instrumental/vocal tracks.
- Stored the extracted tracks in MinIO for retrieval.

### 5. Configuring MinIO for Storage
- Deployed MinIO within Kubernetes for storing MP3 files and extracted audio tracks.
- Configured access credentials and storage buckets (`queue` for raw MP3 files, `output` for processed tracks).

### 6. Monitoring and Debugging
- Used Kubernetes logs and `kubectl port-forward` for local debugging.
- Implemented a logging service using Redis to track processing events.

## Deployment Steps
1. **Deploy Redis and MinIO**:
   ```sh
   kubectl apply -f redis-deployment.yaml
   kubectl apply -f minio-deployment.yaml
   ```
2. **Deploy the REST API**:
   ```sh
   kubectl apply -f rest-deployment.yaml
   ```
3. **Deploy the Worker Service**:
   ```sh
   kubectl apply -f worker-deployment.yaml
   ```
4. **Test the System Using Sample Requests**:
   ```sh
   python sample-requests.py
   ```

## Challenges Faced
- **Memory Constraints**: The Demucs model required significant memory, requiring optimizations in worker scaling.
- **Efficient Task Scheduling**: Implemented Redis-based queuing to balance workloads between worker nodes.
- **Container Versioning**: Used explicit versioning for Docker images to ensure smooth deployment updates.

## Outcome
This project successfully implemented an end-to-end microservices-based system for automatic music separation using Kubernetes. It showcases expertise in cloud-native development, container orchestration, and distributed task processing.

