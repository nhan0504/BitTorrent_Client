import socket
import struct
import queue
import hashlib
from share_type import TorrentMetaData, Message, MSG_ID

BLOCK_LENGTH = 65536000

def create_handshake(info_hash, peer_id):
    pstrlen = 19  
    pstr = b"BitTorrent protocol"  
    reserved = b"\x00" * 8  
    
    handshake = struct.pack(">B19s8s20s20s", pstrlen, pstr, reserved, info_hash, peer_id.encode('utf-8'))
    return handshake

def connect_to_peer(peer, info_hash, peer_id):
    ip = peer["ip"]
    port = peer["port"]
    
    try:
        # 1. Establish TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        sock.connect((ip, port))

        # 2. Send handshake
        handshake = create_handshake(info_hash, peer_id)
        sock.sendall(handshake)

        response = sock.recv(68)
        if len(response) == 68:
            print(f"Connected successfully to {ip}:{port}")
            return sock
        else:
            sock.close()
            return None 
        
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return None
    
def read_message(socket):
    length_bytes = socket.recv(4)
    message_length = struct.unpack("!I", length_bytes)[0]
    
    # Check for keep-alive message (length == 0)
    if message_length == 0:
        return None
    
    # Read the full message as indicated by the length prefix
    message = socket.recv(message_length)
    message_id = message[0]  
    payload = message[1:]   

    return Message(id=message_id, payload=payload)

def handle_message(message: Message, socket):
    if message.id == MSG_ID.CHOKE:
        print("I got choked")
    elif message.id == MSG_ID.UNCHOKE:
        msg = read_message(socket=socket)
        handle_message(msg, socket)
    elif message.id == MSG_ID.HAVE:
        print("I have a piece")
    elif message.id == MSG_ID.BITFIELD:
        print("These are the pieces peer has")
    elif message.id == MSG_ID.PIECE:
        print("I send you this piece")

def parse_bitfield(payload):
    pieces = set()
    for byte_index, byte in enumerate(payload):
        for bit in range(8):
            if byte & (1 << (7 - bit)):
                piece_index = byte_index * 8 + bit
                pieces.add(piece_index)
    return pieces

def peer_available_pieces(socket):
    message = read_message(socket=socket)
    if message:
        return parse_bitfield(message.payload)
    return None

def download_one_piece_from_peer(socket, pieces, job_queue: queue, torrent_meta_data: TorrentMetaData):
    while True:
        try:
            piece_idx = job_queue.get(block=False)
            # Check if peer have the piece in the job
            if (piece_idx in pieces):
                # Download this piece
                # Break the piece down into 2^16 KB block for TCP request
                # Build request message
                for offset in range(0, torrent_meta_data.piece_length, BLOCK_LENGTH):
                    if (offset + BLOCK_LENGTH) <= torrent_meta_data.piece_length:
                        block_length = BLOCK_LENGTH
                    else:
                        block_length = torrent_meta_data.piece_length - offset
                    
                    payload = struct.pack("!III", piece_idx, offset, block_length)
                    request_msg = Message(MSG_ID.REQUEST, payload=payload)
                    socket.sendall(request_msg.to_bytes())

                    # Get the response which is a Piece message
                    message = read_message(socket=socket)
                    
                    # Min heap to hold all the block 
                    blocks_minheap = queue.PriorityQueue()
                    piece_index = struct.unpack("!I", message.payload[0:4])[0]
                    begin = struct.unpack("!I", message.payload[4:8])[0]
                    block = message.payload[8:]

                    blocks_minheap.put((begin, block))

                    # Assemble the block into a whole piece
                    while not blocks_minheap.empty():
                        piece += blocks_minheap.get()[1]

                    # Check the piece hash
                    downloaded_piece_hash = hashlib.sha1(piece).digest()
                    if downloaded_piece_hash == torrent_meta_data.hash[piece_idx]:
                        # Return the downloaded piece in the end
                        return piece
                    else:
                        job_queue.put(piece_idx)             
            else:
                job_queue.put(piece_idx)
                continue
        except queue.Empty:
            return None