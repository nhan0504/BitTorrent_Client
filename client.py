from tkinter import Tk, filedialog
from parser import parse_torrent_file
from tracker import connect_to_tracker
from peers import connect_to_peer, peer_available_pieces, download_one_piece_from_peer
from share_type import TrackerResponse, Message, MSG_ID
import random
import queue
import time

Tk().withdraw() 
file_path = filedialog.askopenfilename(title="Select a Torrent File", filetypes=[("Torrent Files", "*.torrent")])

def generate_peer_id():
    """Generate a 20-byte peer ID"""
    return "-PC0001-" + "".join([str(random.randint(0, 9)) for _ in range(12)])

def connect_to_available_peer(peer_queue):
    while True:
        try:
            peer = peer_queue.get(timeout=interval)
            sock = connect_to_peer(peer=peer, info_hash=torrent_meta_data.info_hash, peer_id=peer_id)
            if sock:
                return sock                
            else:
               continue
        except queue.Empty:
            return None       

if file_path:
    torrent_meta_data = parse_torrent_file(file_path)

    # Generate a peer ID to identify ourselves to other peer
    peer_id = generate_peer_id()

    # Interval that we have to reconnect with tracker
    interval = 0

    # Queue for job
    job_queue = queue.Queue()
    for i in range(torrent_meta_data.num_pieces):
        job_queue.put(i)
    # Queue for peer
    peer_queue = queue.Queue()

    # Number of thread
    NUM_THREAD = 1

    # Last time we connect to tracker 
    prev_time = 0

    # Reconnect to tracker every interval to get peers list
    if interval == 0:
        tracker_response: TrackerResponse = connect_to_tracker(torrent_meta_data=torrent_meta_data, peer_id=peer_id)
        # print("tracker response: ", tracker_response.interval, tracker_response.peers)
        interval = tracker_response.interval
        for peer in tracker_response.peers:
            peer_queue.put(peer)
    elif prev_time + interval >= time.time(): 
        tracker_response: TrackerResponse = connect_to_tracker(torrent_meta_data=torrent_meta_data, peer_id=peer_id)
        for peer in tracker_response.peers:
            peer_queue.put(peer)
        # print("tracker response: ", tracker_response)


    #1. Connect to a peer
    socket = connect_to_available_peer(peer_queue=peer_queue)

    #2. Receive Bitfield message
    pieces = peer_available_pieces(socket=socket)
    #TODO: if piecs is empty
    # print(pieces)

    #3. Send interested message
    interest_msg = Message(id=MSG_ID.INTERESTED)
    socket.sendall(interest_msg.to_bytes())
    print('Send interested message')

    #4. Get unchoked message from peer
    download_one_piece_from_peer(socket, pieces, job_queue, torrent_meta_data=torrent_meta_data)
    socket.close()