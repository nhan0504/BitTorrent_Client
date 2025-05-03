import socket
import struct
import queue
import hashlib
from share_type import TorrentMetaData, Message, MSG_ID, PeerConnection

BLOCK_LENGTH = 16 * 1024

def create_handshake(info_hash, peer_id):
    pstrlen = 19  
    pstr = b"BitTorrent protocol"  
    reserved = b"\x00" * 8  
    
    handshake = struct.pack(">B19s8s20s20s", pstrlen, pstr, reserved, info_hash, peer_id.encode('utf-8'))
    return handshake

def parse_handshake(response: bytes) -> (bytes, str):
    if len(response) != 68:
        raise ValueError("Handshake must be exactly 68 bytes")

    pstrlen, pstr, reserved, their_info_hash, raw_peer_id = struct.unpack(
        ">B19s8s20s20s", response
    )
    if pstrlen != 19 or pstr != b"BitTorrent protocol":
        raise ValueError("Invalid protocol header in handshake")

    peer_id = raw_peer_id.decode("utf-8", errors="ignore")
    return their_info_hash, peer_id

def connect_to_peer(peer, info_hash, peer_id):
    ip = peer["ip"]
    port = peer["port"]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    
    try:
        # 1. Establish TCP connection  
        sock.connect((ip, port))

        # 2. Send handshake
        handshake = create_handshake(info_hash, peer_id)
        sock.sendall(handshake)

        response = sock.recv(68)
        print("raw handshake:", response[:20], repr(response[20:]))
        peer_info_hash, peer_id = parse_handshake(response)
        if peer_info_hash != info_hash:
            print(f"Peer {ip}:{port} has wrong info_hash, closing")
            sock.close()
            return None

        print("Connect sucessfully to peer:", ip, port)
        return PeerConnection(sock, peer_id, info_hash)
        
    except (socket.timeout, ConnectionRefusedError, ValueError, ConnectionError) as e:
        print(f"connect_to_peer({ip}:{port}) failed: {e}")
        sock.close()
        return None

def download_available_pieces(
    conn: PeerConnection,
    torrent_meta: TorrentMetaData,
    needed_pieces: set[int],
    file_handle,
    progress_callback=None
) -> None:
    try:
        # Send interest message & wait
        conn.send_interested()
        # Wait for the peer to send a bitfield message
        conn.await_bitfield()
        
        num_pieces = torrent_meta.num_pieces
        piece_len = torrent_meta.piece_length


        print("Start downloading pieces...")
        for index in sorted(needed_pieces):
            # Check if the peer has this piece
            if index not in conn.available_pieces:
                print(f"Peer does not have piece {index}, skipping")
                continue 

            # compute the length of the piece
            if index == num_pieces - 1:
                this_len = torrent_meta.length - piece_len * (num_pieces - 1)
            else:
                this_len = piece_len

            buffer = bytearray(this_len)

            # Send request message for each block
            for begin in range(0, this_len, BLOCK_LENGTH):
                blen = min(BLOCK_LENGTH, this_len - begin)

                # Wait until we are unchoked 
                while conn.choked:
                    msg_id, _ = conn.read_message()
                    if msg_id == MSG_ID.UNCHOKE.value:
                        conn.choked = False
                    elif msg_id == MSG_ID.HAVE.value:
                        (piece_index,) = struct.unpack(">I", payload)
                        conn.available_pieces.add(piece_index)
                
                conn.send_request(index, begin, blen)

                # wait for the matching PIECE
                while True:
                    msg_id, payload = conn.handle_peer_messages()
                    
                    if msg_id == MSG_ID.PIECE.value:
                        rec_index = struct.unpack(">I", payload[:4])[0]
                        rec_begin = struct.unpack(">I", payload[4:8])[0]
                        data = payload[8:]
                        if rec_index == index and rec_begin == begin:
                            buffer[begin:begin+len(data)] = data
                            break
                    # Ignore for now
                    elif msg_id == MSG_ID.REQUEST.value:
                        continue
                    elif msg_id == MSG_ID.CANCEL.value:
                        continue

            # verify SHA-1
            if hashlib.sha1(buffer).digest() != torrent_meta.hash[index]:
                continue 

            # write the piece into file at correct offset
            file_handle.seek(index * piece_len)
            file_handle.write(buffer)
            file_handle.flush()

            # Remove the piece from the set of needed pieces
            print(f"Downloaded piece {index}")
            needed_pieces.remove(index)
            if progress_callback:
                progress_callback(torrent_meta.num_pieces - len(needed_pieces))
    except ConnectionError as e:
        print(f"[{conn.peer_id}] disconnected mid‐download: {e}")
    finally:
        conn.close()