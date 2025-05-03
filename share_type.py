import struct
import socket
import math
from enum import Enum

class MSG_ID(Enum):
    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7
    CANCEL = 8

class TorrentMetaData:
    def __init__(self, announce: str, info_hash: bytes, name: str, piece_length: int, pieces: bytes, length: int):
        self.announce = announce
        self.info_hash = info_hash
        self.piece_length = piece_length
        self.name = name
        self.length = length
        self.num_pieces = math.ceil(length / piece_length)
        self.hash = [pieces[i:i+20] for i in range(0, len(pieces), 20)]

    def get_pieces_hash_array(self, chunk_size = 20) -> list[bytes]:
        return [self.pieces[i:i+chunk_size] for i in range(0, len(self.pieces), chunk_size)]

class TrackerResponse:
    def __init__(self, interval: int, peers: list):
        self.interval = interval
        self.peers = peers

class Message:
    def __init__(self, id, payload=b""):
        self.id = id
        self.payload = payload

    def to_bytes(self) -> bytes:
        # Total length = 1 byte for id + payload length
        message_length = 1 + len(self.payload)
        length_prefix = struct.pack("!I", message_length)
        message_id_byte = bytes(self.id)
        return length_prefix + message_id_byte + self.payload

class PeerConnection:
    def __init__(self, sock: socket.socket, peer_id: str, info_hash: bytes):
        self.sock       = sock
        self.peer_id    = peer_id
        self.info_hash  = info_hash
        self.available_pieces   = set()    
        self.choked     = True
        self.interested = False
    
    def recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            try:
                chunk = self.sock.recv(n - len(buf))
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                raise ConnectionError(f"Socket read failed: {e}")
            if not chunk:
                raise ConnectionError("Peer closed connection")
            buf += chunk
        return buf

    def parse_bitfield(self, payload: bytes):
        self.available_pieces.clear()
        for i in range(len(payload) * 8):
            byte_index = i // 8
            bit_offset = 7 - (i % 8)
            if payload[byte_index] & (1 << bit_offset):
                self.available_pieces.add(i)

    def send(self, data: bytes):
        self.sock.sendall(data)
    
    def send_interested(self):
        length_prefix = struct.pack(">I", 1)                   
        msg_id = bytes([MSG_ID.INTERESTED.value])     
        self.send(length_prefix + msg_id)
        self.interested = True

    def send_request(self, index: int, begin: int, length: int):
        length_prefix = struct.pack(">I", 13)
        msg_id        = bytes([MSG_ID.REQUEST.value])
        body          = struct.pack(">III", index, begin, length)
        self.send(length_prefix + msg_id + body)

    def read_message(self):
        # 1) read the 4-byte length prefix
        raw_len = self.recv_exact(4)
        msg_len = struct.unpack(">I", raw_len)[0]

        # 2) keep-alive has no payload
        if msg_len == 0:
            return ("keep-alive", None)

        # 3) read the rest (1-byte ID + (msg_len-1) payload)
        data = self.recv_exact(msg_len)
        msg_id  = data[0]
        payload = data[1:]
        return msg_id, payload

    def handle_peer_messages(self):
        while True:
            msg_id, payload = self.read_message()

            # keep-alive
            if msg_id == "keep-alive":
                continue

            # choke
            if msg_id == MSG_ID.CHOKE.value:
                self.choked = True
                print("Got choked")
                continue

            # unchoke
            if msg_id == MSG_ID.UNCHOKE.value:
                self.choked = False
                print("Got unchoked")
                continue

            # have
            if msg_id == MSG_ID.HAVE.value:
                (piece_index,) = struct.unpack(">I", payload)
                self.available_pieces.add(piece_index)
                continue

            # bitfield
            if msg_id == MSG_ID.BITFIELD.value:
                self.parse_bitfield(payload)
                continue

            # 6) everything else (REQUEST, PIECE, CANCEL) bubble up
            return msg_id, payload

    def await_bitfield(self):
        while self.available_pieces == set():
            msg_id, payload = self.read_message()

            # keep-alive -> ignore
            if msg_id == "keep-alive":
                continue

            # BITFIELD -> record which pieces the peer has
            if msg_id == MSG_ID.BITFIELD.value:
                self.parse_bitfield(payload)

    def close(self):
        self.sock.close()