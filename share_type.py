class TorrentMetaData:
    def __init__(self, announce: str, info_hash: bytes, name: str, piece_length: int, pieces: bytes, length: int):
        self.announce = announce
        self.info_hash = info_hash
        self.name = name
        self.piece_length = piece_length
        self.pieces = pieces
        self.length = length

    def get_pieces_hash_array(self, chunk_size = 20) -> list[bytes]:
        return [self.pieces[i:i+chunk_size] for i in range(0, len(self.pieces), chunk_size)]
