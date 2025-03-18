from tkinter import Tk, filedialog
from parser import parse_torrent_file
from tracker import connect_to_tracker
from peers import connect_to_peer
import random

Tk().withdraw() 
file_path = filedialog.askopenfilename(title="Select a Torrent File", filetypes=[("Torrent Files", "*.torrent")])

def generate_peer_id():
    """Generate a 20-byte peer ID"""
    return "-PC0001-" + "".join([str(random.randint(0, 9)) for _ in range(12)])

if file_path:
    torrent_meta_data = parse_torrent_file(file_path)

    # Generate a peer ID to identify ourselves to other peer
    peer_id = generate_peer_id()

    # Connect to tracker and get peers list
    tracker_response = connect_to_tracker(torrent_meta_data=torrent_meta_data, peer_id=peer_id)
    print("tracker response: ", tracker_response)

    # Connect to peers
    connect_to_peer(peer=tracker_response["peers"][0], info_hash=torrent_meta_data.info_hash, peer_id=peer_id)
    connect_to_peer(peer=tracker_response["peers"][1], info_hash=torrent_meta_data.info_hash, peer_id=peer_id)
    
