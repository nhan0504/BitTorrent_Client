import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from parser import parse_torrent_file
from tracker import connect_to_tracker
from peers import connect_to_peer, download_available_pieces
from share_type import TrackerResponse
import random
import time
import threading

def generate_peer_id():
    """Generate a 20-byte peer ID"""
    return "-PC0001-" + "".join([str(random.randint(0, 9)) for _ in range(12)])

class TorrentDownloaderApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BitTorrent Client")
        self.root.geometry("520x200")

        # Select button
        self.select_btn = ttk.Button(
            self.root,
            text="Select .torrent File...",
            command=self.select_torrent
        )
        self.select_btn.pack(pady=15)

        # Progress bar
        self.progress = ttk.Progressbar(
            self.root,
            length=450,
            mode="determinate"
        )
        self.progress.pack(pady=5)

        # Status label
        self.status = ttk.Label(self.root, text="Awaiting torrent selection...")
        self.status.pack(pady=5)

        self.root.mainloop()

    def gui_update(self, downloaded: int):
        self.progress['value'] = downloaded
        self.status.config(
            text=f"{downloaded} / {self.progress['maximum']} pieces downloaded"
        )
        self.root.update()

    def select_torrent(self):
        path = filedialog.askopenfilename(
            title="Select a Torrent File",
            filetypes=[("Torrent Files", "*.torrent")]
        )
        if not path:
            return

        # disable UI while running
        self.select_btn.config(state=tk.DISABLED)
        self.status.config(text="Parsing .torrent file…")
        self.root.update()

        try:
            meta = parse_torrent_file(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse torrent: {e}")
            self.select_btn.config(state=tk.NORMAL)
            return

        total = meta.num_pieces
        print(f"Total pieces: {total}")
        self.progress.config(maximum=total, value=0)

        self.status.config(text="Contacting tracker…")
        self.root.update()

        peer_id = generate_peer_id()
        tr = connect_to_tracker(meta, peer_id)
        if not tr or not tr.peers:
            messagebox.showerror("Error", "No peers returned by tracker.")
            self.select_btn.config(state=tk.NORMAL)
            return

        # Merge and manage peer list
        peers = tr.peers.copy()
        seen = {(p['ip'], p['port']) for p in peers}
        last_announce = time.time()
        interval = tr.interval

        # Pre-allocate output file
        out_name = meta.name.decode() if isinstance(meta.name, (bytes, bytearray)) else str(meta.name)
        with open(out_name, "wb") as f:
            f.truncate(meta.length)

        needed = set(range(total))

        # Open for read/write
        with open(out_name, "r+b") as f:
            # Loop until done or no more peers
            i = 0
            while needed and i < len(peers):
                peer = peers[i]
                i += 1

                # re-announce if needed
                if time.time() - last_announce >= interval:
                    self.status.config(text="Re-announcing to tracker…")
                    self.root.update()
                    new_tr = connect_to_tracker(meta, peer_id)
                    if new_tr and new_tr.peers:
                        for p in new_tr.peers:
                            tpl = (p['ip'], p['port'])
                            if tpl not in seen:
                                peers.append(p)
                                seen.add(tpl)
                        interval = new_tr.interval
                        last_announce = time.time()

                self.status.config(text=f"Connecting to {peer['ip']}:{peer['port']}…")
                self.root.update()

                conn = connect_to_peer(peer, meta.info_hash, peer_id)
                if not conn:
                    continue

                # Download available pieces, updating GUI
                download_available_pieces(
                    conn, meta, needed, f,
                    progress_callback=self.gui_update
                )
                conn.close()

        # Final status
        if not needed:
            self.status.config(text=f"Download complete: {out_name}")
        else:
            self.status.config(text=f"Missing {len(needed)} pieces")

        self.select_btn.config(state=tk.NORMAL)


if __name__ == "__main__":
    TorrentDownloaderApp()
