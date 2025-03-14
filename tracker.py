import requests
import random
import bencodepy

def connect_to_tracker(torrent_data):
    announce_url = torrent_data["announce"]
    info_hash = bytes.fromhex(torrent_data["info_hash"])  
    peer_id = generate_peer_id()
    port = 6881  

    params = {
        "info_hash": info_hash,
        "peer_id": peer_id,
        "port": port,
        "uploaded": 0,
        "downloaded": 0,
        "left": torrent_data["length"],  
        "compact": 1,
        "event": "started"  
    }
    print("params", params)

    # Send GET request
    try:
        response = requests.get(announce_url, params=params, timeout=5)
        response.raise_for_status()  

        tracker_response = bencodepy.decode(response.content)
        print("Tracker Response:", tracker_response)

    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to tracker: {e}")

def generate_peer_id():
    """Generate a 20-byte peer ID"""
    return "-PC0001-" + "".join([str(random.randint(0, 9)) for _ in range(12)])