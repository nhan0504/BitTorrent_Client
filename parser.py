import bencodepy 
import hashlib
from share_type import TorrentMetaData

def parse_torrent_file(file_path):
    # Read in the byte of the file
    with open(file_path, "rb") as f:
        torrent_data = f.read()

    # Decode the .torrent file
    decoded_torrent = bencodepy.decode(torrent_data)

    # Get info
    info_decoded = decoded_torrent.get(b'info', None)

    # Compute the info hash
    info_bencoded = bencodepy.encode(info_decoded)
    info_hash = hashlib.sha1(info_bencoded).digest()

    torrent_parsed_data = TorrentMetaData(
        announce=decoded_torrent.get(b'announce', None).decode('utf-8'), 
        info_hash=info_hash , 
        name=info_decoded.get(b'name', None),
        piece_length=info_decoded.get(b'piece length', None),
        pieces=info_decoded.get(b'pieces', None),
        length=info_decoded.get(b'length', None)
    )

    return torrent_parsed_data