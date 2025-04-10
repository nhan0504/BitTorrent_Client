from tkinter import Tk, filedialog
from parser import parse_torrent_file
from tracker import connect_to_tracker
from peers import connect_to_peer, peer_available_pieces, download_one_piece_from_peer, read_message
from share_type import TrackerResponse, Message, MSG_ID
import random
import queue
import time
import threading

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

def pieces_set_contains_needed_pieces(needed_pieces_queue: queue.Queue, pieces: set):
    # Lock the queue to prevent changes while turning it into a set
    with needed_pieces_queue.mutex:
        job_set = set(needed_pieces_queue.queue)
    return len(job_set.intersection(pieces)) > 0


def connect_and_download(peer_queue, needed_pieces_queue):
    #1. Connect to a peer 
    socket = connect_to_available_peer(peer_queue=peer_queue)

    #2. Receive Bitfield message
    pieces_set = peer_available_pieces(socket=socket)
    if pieces_set == None or len(pieces_set) == 0:
        return
    # print(pieces)

    #3. Send interested message if pieces_set intersect needed_pieces_queue
    if pieces_set_contains_needed_pieces(pieces_set, needed_pieces_queue):
        interest_msg = Message(id=MSG_ID.INTERESTED.value)
        socket.sendall(interest_msg.to_bytes())
        print('Send interested message')
    else:
        return

    #4. Wait for unchoke
    # socket.settimeout()
    while True:
        message = read_message(socket=socket)
        if message.id == MSG_ID.HAVE.value:
            #TODO: Update the pieces set
            continue
        elif message.id == MSG_ID.UNCHOKE.value:
            break

    #4. Get unchoked message from peer
    while not needed_pieces_queue.empty:
        piece_idx = needed_pieces_queue.get(block=False)
        download_one_piece_from_peer(socket, pieces, needed_pieces_queue, torrent_meta_data=torrent_meta_data)
    socket.close()   

if file_path:
    NUM_THREAD = 1
    torrent_meta_data = parse_torrent_file(file_path)

    peer_id = generate_peer_id()   # Peer ID to identify ourselves to other peer
    interval = 0   # Interval that we have to reconnect with tracker

    # Queue for job
    needed_pieces_queue = queue.Queue()
    for i in range(torrent_meta_data.num_pieces):
        needed_pieces_queue.put(i)

    # Queue for peer
    peer_queue = queue.Queue()

    prev_time = time.time()   # Last time we connect to tracker 
    # Reconnect to tracker every interval to get peers list
    if prev_time + interval <= time.time(): 
        tracker_response: TrackerResponse = connect_to_tracker(torrent_meta_data=torrent_meta_data, peer_id=peer_id)
        interval = tracker_response.interval
        for peer in tracker_response.peers:
            peer_queue.put(peer)
        # print("tracker response: ", tracker_response)

    connect_and_download(peer_queue, needed_pieces_queue)