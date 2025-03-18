import socket
import struct

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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5) 
        print(f"Connecting to {ip}:{port}...")
        
        sock.connect((ip, port))
        print(f"Connected to {ip}:{port}")

        handshake = create_handshake(info_hash, peer_id)
        sock.send(handshake)
        print("Handshake sent!")

        response = sock.recv(68)
        if len(response) == 68:
            print(f"Received handshake response from {ip}:{port}")
        else:
            print(f"Invalid handshake response from {ip}:{port}")
        
        sock.close()
        
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"Failed to connect to {ip}:{port}: {e}")