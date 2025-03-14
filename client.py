from tkinter import Tk, filedialog
from parser import parse_torrent_file
from tracker import connect_to_tracker

Tk().withdraw() 
file_path = filedialog.askopenfilename(title="Select a Torrent File", filetypes=[("Torrent Files", "*.torrent")])

if file_path:
    torrent_data = parse_torrent_file(file_path)
    print(torrent_data)
    connect_to_tracker(torrent_data=torrent_data)