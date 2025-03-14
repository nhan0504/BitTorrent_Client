import bencodepy
import hashlib

def parse_torrent_file(file_path):
    # Read in the byte of the file
    with open(file_path, "rb") as f:
        torrent_data = f.read()

    # Decode the .torrent file
    decoded_torrent = bencodepy.decode(torrent_data)

    # Extract announce URL (tracker URL)
    announce_url = decoded_torrent.get(b'announce', None)
    if announce_url:
        announce_url = announce_url.decode('utf-8')
    else:
        announce_url = "No tracker found"

    # Get info
    info_decoded = decoded_torrent.get(b'info', None)
    info_bencoded = bencodepy.encode(info_decoded)

    # Compute the info hash
    info_hash = hashlib.sha1(info_bencoded).hexdigest()

    # Get length
    length = info_decoded.get(b'length', None)

    # Get name
    name = info_decoded.get(b'name', None)

    # Get piece length
    piece_length = info_decoded.get(b'piece length', None)

    # Get pieces
    pieces = info_decoded.get(b'pieces', None)

    return {
        "announce": announce_url,
        "info_hash": info_hash ,
        "name": name,
        "piece_length": piece_length,
        "pieces": pieces,
        "length": length
    }