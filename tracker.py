import requests
import bencodepy
import struct
from share_type import TorrentMetaData, TrackerResponse


def connect_to_tracker(torrent_meta_data: TorrentMetaData, peer_id) -> TrackerResponse:
    announce_url = torrent_meta_data.announce
    port = 6881  

    params = {
        "info_hash": torrent_meta_data.info_hash,
        "peer_id": peer_id,
        "port": port,
        "uploaded": 0,
        "downloaded": 0,
        "left": torrent_meta_data.length,  
        "compact": 1,
        "event": "started"  
    }

    # Send GET request
    try:
        response = requests.get(announce_url, params=params, timeout=5)
        response.raise_for_status()  

        tracker_response = bencodepy.decode(response.content)
        return TrackerResponse(tracker_response[b'interval'], parse_peers(tracker_response[b'peers']))
        

    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to tracker: {e}")

def parse_peers(peers_data):
    if isinstance(peers_data, list):
        # Case 1: Peers as a list of dictionaries (non-compact format)
        peers = [
            {
                "peer_id": peer[b'peer id'].decode(errors='ignore'),
                "ip": peer[b'ip'].decode(),
                "port": peer[b'port']
            }
            for peer in peers_data
        ]
    elif isinstance(peers_data, bytes):
        # Case 2: Compact format (binary blob)
        peers = []
        for i in range(0, len(peers_data), 6): 
            ip = ".".join(str(b) for b in peers_data[i:i+4])    
            port = struct.unpack(">H", peers_data[i+4:i+6])[0]  
            peers.append({"ip": ip, "port": port})
    else:
        peers = []

    return peers