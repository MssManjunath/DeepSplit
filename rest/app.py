from flask import Flask, request, jsonify, send_file
import redis
import json
import os
from minio import Minio
from minio.error import S3Error
import base64
from io import BytesIO


app = Flask(__name__)

# Redis setup
redis_host = 'redis'
redis_port = 6379
r = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)

minio_endpoint = os.getenv('MINIO_ENDPOINT', 'minio-proj.minio-ns.svc.cluster.local:9000')
minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'rootuser')
minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'rootpass123')

minio_client = Minio(
    minio_endpoint,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=False
)

bucket_name = "songs"



@app.route('/apiv1/separate', methods=['POST'])
def separate():
    print("Received POST request to /apiv1/separate")

    data = request.json
    
    # Extract base64-encoded MP3 data
    song_data_b64 = data.get('mp3')
    if not song_data_b64:
        return jsonify({"error": "No MP3 file provided"}), 400
    
    try:
        song_data = base64.b64decode(song_data_b64)
    except Exception as e:
        return jsonify({"error": "Failed to decode MP3 file", "details": str(e)}), 400

    songhash = f"song_{r.incr('song_count')}"

    song_key = f"songs/{songhash}.mp3"

    try:
        minio_client.put_object(
            bucket_name, 
            song_key, 
            data=BytesIO(song_data),
            length=len(song_data),
            content_type='audio/mpeg'
        )
        print(f"Song uploaded to MinIO with key {song_key}")
    except S3Error as e:
        return jsonify({"error": "Failed to upload MP3 file to MinIO", "details": str(e)}), 500

    r.lpush('toWorker', json.dumps({'songhash': songhash, 'song_key': song_key}))
    
    return jsonify({'hash': songhash, 'reason': 'Song enqueued for separation'}), 200


@app.route('/apiv1/fetch_songs', methods=['GET'])
def list_songs():
    try:
        objects = minio_client.list_objects("separated-tracks", recursive=True)
        songs = []
        for obj in objects:
            song_hash = obj.object_name.split('/')[0]
            song_size = obj.size  # Size of the song file
            songs.append({"hash": song_hash, "size": song_size})
        
        # Return the list as a JSON response
        return jsonify({"songs": songs}), 200

    except S3Error as e:
        return jsonify({"error": f"Failed to list songs: {str(e)}"}), 500

@app.route('/apiv1/queue', methods=['GET'])
def queue():
    # Retrieve all queued songs
    queue = r.lrange('toWorker', 0, -1)
    return jsonify({'queue': queue}), 200

def get_track_key(songhash, track_name):
    return f"{songhash}/{track_name}.mp3"

# Endpoint to retrieve a track
@app.route('/apiv1/track/<songhash>/track', methods=['GET'])
def get_track(songhash):
    track_name = request.args.get('track')    
    if not track_name or track_name not in ["bass", "vocals", "drums", "other"]:
        return jsonify({"error": "Invalid track name. Must be 'bass', 'vocals', 'drums', or 'other'."}), 400
    
    track_key = get_track_key(songhash, track_name)
    
    try:
        # Check if the track exists in the bucket
        minio_client.stat_object("separated-tracks", track_key)
        
        # Send the file as a binary response
        return send_file(
            minio_client.get_object("separated-tracks", track_key),
            as_attachment=True,
            download_name=f"{track_name}.mp3",
            mimetype="audio/mp3"
        )
    except S3Error as e:
        return jsonify({"error": f"Track '{track_name}' for song '{songhash}' not found."}), 404

# Endpoint to remove a track
@app.route('/apiv1/remove/<songhash>/track', methods=['GET'])
def remove_track(songhash):
    track_name = request.args.get('track')
    
    if not track_name or track_name not in ["bass", "vocals", "drums", "other"]:
        return jsonify({"error": "Invalid track name. Must be 'bass', 'vocals', 'drums', or 'other'."}), 400

    track_key = get_track_key(songhash, track_name)
    
    try:
        # Check if the track exists in the bucket and remove it
        minio_client.remove_object("separated-tracks", track_key)
        return jsonify({"message": f"Track '{track_name}' for song '{songhash}' has been removed."}), 200
    except S3Error as e:
        return jsonify({"error": f"Failed to remove track '{track_name}' for song '{songhash}': {str(e)}"}), 500

@app.route('/', methods=['GET'])
def health_check():
    return '<h1> Music Separation Server</h1><p> Use a valid endpoint </p>'

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
