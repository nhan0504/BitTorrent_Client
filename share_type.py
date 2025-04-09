import struct
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
        self.num_pieces = int (length / piece_length)
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