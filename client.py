import tkinter as tk
from tkinter import filedialog
from parser import parse_torrent_file
from tracker import connect_to_tracker
from peers import connect_to_peer, download_available_pieces
from share_type import TrackerResponse, Message, MSG_ID
import random
import queue
import time
import threading

def generate_peer_id():
    """Generate a 20-byte peer ID"""
    return "-PC0001-" + "".join([str(random.randint(0, 9)) for _ in range(12)])

def main():
    root = tk.Tk()
    root.withdraw()  
    file_path = filedialog.askopenfilename(
        title="Select a Torrent File",
        filetypes=[("Torrent Files", "*.torrent")]
    )

    torrent_meta_data = parse_torrent_file(file_path)
    my_id = generate_peer_id()
    tracker_resp = connect_to_tracker(torrent_meta_data, my_id)

    peers_list = tracker_resp.peers

    out_fname = torrent_meta_data.name.decode("utf-8")

    # Create a file to save the downloaded data
    with open(out_fname, "wb") as f:
        f.truncate(torrent_meta_data.length)

    # set of needed pieces
    needed = set(range(torrent_meta_data.num_pieces))

    with open(out_fname, "r+b") as f:
        for peer in peers_list:
            if not needed:
                break

            print(f"Connecting to {peer['ip']}:{peer['port']} …")
            conn = connect_to_peer(peer, torrent_meta_data.info_hash, my_id)
            if not conn:
                continue

            try:
                download_available_pieces(conn, torrent_meta_data, needed, f)
            finally:
                conn.close()

    if not needed:
        print(f"Finish downloading: {out_fname}")
    else:
        print("All peers failed. Could not download file.")

if __name__ == "__main__":
    main()