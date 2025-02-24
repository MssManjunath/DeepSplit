import os
import redis
import json
import requests
from minio import Minio
from demucs import separate
import torchaudio
torchaudio.set_audio_backend("sox_io")

# Redis and MinIO setup
minio_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'rootuser')
minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'rootpass123')
redis_host = os.getenv('REDIS_HOST', 'localhost')

print(f"MinIO Endpoint: {minio_endpoint}")
print(f"MinIO Access Key: {minio_access_key}")
print(f"Redis Host: {redis_host}")

# Set up Redis client
redis_client = redis.StrictRedis(host=redis_host, port=6379, db=0)

# Set up MinIO client
minio_client = Minio(
    minio_endpoint,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=False
)

def log_debug(message):
    redis_client.rpush("logging", f"[DEBUG] {message}")
    print(f"[DEBUG] {message}")

def log_info(message):
    redis_client.rpush("logging", f"[INFO] {message}")
    print(f"[INFO] {message}")

def log_error(message):
    redis_client.rpush("logging", f"[ERROR] {message}")
    print(f"[ERROR] {message}")

def process_request(data):
    song_key = data.get("song_key")
    song_hash = data.get("songhash")
    
    log_info(f"Processing request with song_key: {song_key} and song_hash: {song_hash}")
    
    if not song_key or not song_hash:
        log_error(f"Missing required keys in data: {data}")
        return

    try:
        # Ensure that MinIO buckets exist
        if not minio_client.bucket_exists("songs"):
            minio_client.make_bucket("songs")
            log_info("Bucket 'songs' created successfully.")
        if not minio_client.bucket_exists("separated-tracks"):
            minio_client.make_bucket("separated-tracks")
            log_info("Bucket 'separated-tracks' created successfully.")
    except Exception as e:
        log_error(f"Error checking or creating buckets: {e}")
        return

    # Ensure the song is downloaded to a valid local path
    song_path = os.path.join(r"C:\tmp", f"{song_hash}.mp3")
    log_info(f"Downloading song with key {song_key}")
    try:
        minio_client.fget_object("songs", song_key, song_path)
        log_info(f"Successfully downloaded song {song_hash}")
    except Exception as e:
        log_error(f"Error downloading song {song_hash}: {e}")
        return

    # Run DEMUCS to separate tracks
    log_info(f"Starting separation for song {song_hash}")
    try:
        os.system(f"python -m demucs.separate --out C:\\tmp\\output {song_path}")
        log_info(f"Separation completed for song {song_hash}")
    except Exception as e:
        log_error(f"Error running demucs separation for {song_hash}: {e}")
        return

    # Define the correct output directory based on the DEMUCS separation
    output_directory = os.path.join(r"C:\tmp\output\htdemucs", song_hash)
    log_info(f"Separated tracks will be stored in: {output_directory}")

    parts = ["bass", "drums", "vocals", "other"]
    for part in parts:
        wav_path = os.path.join(output_directory, f"{part}.wav")
        mp3_path = os.path.join(output_directory, f"{part}.mp3")
        try:
            if os.path.exists(wav_path):
                # Convert .wav to .mp3
                waveform, sample_rate = torchaudio.load(wav_path)
                torchaudio.save(mp3_path, waveform, sample_rate, format="mp3")
                track_key = f"{song_hash}/{part}.mp3"
                minio_client.fput_object("separated-tracks", track_key, mp3_path)
                log_info(f"Uploaded {part} track for song {song_hash} to MinIO as .mp3")
            else:
                log_error(f"Track {part} not found for song {song_hash} at {wav_path}")
        except Exception as e:
            log_error(f"Error uploading {part} track for song {song_hash}: {e}")
    
    # If a webhook is provided, send the status to the webhook URL
    if "webhook" in data:
        try:
            response = requests.post(data["webhook"], json={"status": "completed", "song_hash": song_hash})
            log_info(f"Webhook callback status: {response.status_code} for song {song_hash}")
        except Exception as e:
            log_error(f"Error sending webhook for song {song_hash}: {e}")

def listen_to_worker_queue():
    while True:
        log_info("Waiting for messages in the 'toWorker' queue.")
        try:
            _, message = redis_client.blpop("toWorker")
            log_info("Received message from 'toWorker' queue.")
            data = json.loads(message)
            process_request(data)
        except Exception as e:
            log_error(f"Error in listen_to_worker_queue: {e}")
            log_info("Waiting for messages in the 'toWorker' queue.")

if __name__ == "__main__":
    log_info("Connecting to Redis...")
    try:
        redis_client.ping()
        log_info("[INFO] Connected to Redis successfully.")
    except Exception as e:
        log_error(f"Error connecting to Redis: {e}")

    log_info("Connecting to MinIO...")
    try:
        minio_client.list_buckets()
        log_info("[INFO] Connected to MinIO successfully.")
    except Exception as e:
        log_error(f"Error connecting to MinIO: {e}")

    log_info("Starting worker queue listener...")
    listen_to_worker_queue()
