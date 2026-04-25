#!/usr/bin/env python3
"""
CPSC 471 - Programming Assignment 1
Simplified FTP Client

Usage: python3 cli.py <SERVER_MACHINE> <SERVER_PORT>
Example: python3 cli.py ecs.fullerton.edu 1234

COLLAB NOTES
  COMPLETED:
    - All imports and constants
    - send_all()           — reliable send loop
    - recv_exact()         — reliable receive loop
    - send_msg()           — framed message sender (10-byte header + payload)
    - recv_msg()           — framed message receiver
    - get_ephemeral_port() — OS-assigned free port for data channel
    - send_file_over_socket() — chunked file upload helper
    - recv_file_over_socket() — chunked file download helper

  TODO:
    - do_ls()  
    - do_get()  
    - do_put()  
    - main()    
    delete this when done pls
"""

import socket
import os
import sys

# Constants
# Every message on the control or data channel
# starts with a 10-byte zero-padded decimal
# header that tells the receiver how many bytes
# of payload follow.  Example: a 47-byte payload
# is preceded by "0000000047".
# CHUNK_SIZE controls how many bytes we read from
# disk at a time — keeps large files from eating
# all available memory.

HEADER_SIZE = 10    # bytes — must match serv.py exactly
CHUNK_SIZE  = 4096  # bytes per file-read chunk

def send_all(sock, data: bytes):
    """
    Sends every byte of data over sock.
    Python's sock.send() is not guaranteed to send all bytes in one call
    it returns however many bytes the OS accepted, which may be less than
    len(data). This function loops, advancing a counter each iteration,
    until every byte has been sent.
    """
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise RuntimeError("Socket connection broken during send")
        total_sent += sent

def recv_exact(sock, n: int) -> bytes:
    """
    Receives exactly n bytes from sock and returns them.
    sock.recv(n) returns as soon as ANY data arrives — even just 1 byte —
    which is the core problem described in the assignment Preliminaries.
    This function loops, appending each chunk to a buffer, until exactly
    n bytes have been accumulated.
    """
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("Socket connection closed before all bytes received")
        buf += chunk
    return buf

def send_msg(sock, payload: bytes):
    """
    Frames and sends a message over the control channel.
    Every message is prefixed with a 10-byte zero-padded ASCII header
    containing the length of the payload, followed by the payload itself.
    Example: a 47-byte payload is sent as "0000000047" + payload bytes.
    The receiver reads the header first to know exactly how many bytes
    to expect, which prevents it from reading too little or too much.
    """
    header = str(len(payload)).zfill(HEADER_SIZE).encode()
    send_all(sock, header + payload)

def recv_msg(sock) -> bytes:
    """
    Receives a framed message from the control channel and returns the payload.
    First reads exactly 10 bytes and parses them as the payload length.
    Then reads exactly that many bytes and returns them.
    This pairs with send_msg() — every message sent by one side is received
    correctly by the other regardless of how TCP splits up the bytes.
    """
    raw_header = recv_exact(sock, HEADER_SIZE)
    payload_len = int(raw_header.decode().strip())
    return recv_exact(sock, payload_len)

def get_ephemeral_port() -> tuple:
    """
    Opens a listening socket on a free port chosen by the OS and returns it.
    The assignment requires a separate data channel for every file transfer.
    The client acts as the passive side: it binds to port 0 (which tells the
    OS to assign any available port), then sends that port number to the server
    over the control channel so the server knows where to connect.
    Returns a tuple of (listen_socket, port_number). The caller is responsible
    for calling listen_socket.accept() when ready to receive the connection.
    """
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind(("", 0))   # port 0 → OS assigns a free port
    listen_sock.listen(1)
    port = listen_sock.getsockname()[1]
    return listen_sock, port

def send_file_over_socket(data_sock, filepath: str) -> int:
    """
    Sends a local file over an already-connected data socket.
    First sends a 10-byte header containing the file size so the receiver
    knows exactly how many bytes to expect. Then reads and sends the file
    in CHUNK_SIZE pieces, which prevents large files from being loaded
    entirely into memory at once. Returns the total number of bytes sent.
    """
    file_size = os.path.getsize(filepath)
    header = str(file_size).zfill(HEADER_SIZE).encode()
    send_all(data_sock, header)

    bytes_sent = 0
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            send_all(data_sock, chunk)
            bytes_sent += len(chunk)
    return bytes_sent

def recv_file_over_socket(data_sock, save_path: str) -> int:
    """
    Receives a file from the data socket and writes it to save_path on disk.
    Reads the 10-byte size header first to learn exactly how many bytes the
    server is sending. Then receives the file in CHUNK_SIZE chunks and writes
    each chunk to disk immediately, so memory usage stays low regardless of
    file size. Returns the total number of bytes written.
    """
    raw_header = recv_exact(data_sock, HEADER_SIZE)
    file_size = int(raw_header.decode().strip())

    bytes_received = 0
    with open(save_path, "wb") as f:
        while bytes_received < file_size:
            to_read = min(CHUNK_SIZE, file_size - bytes_received)
            chunk = data_sock.recv(to_read)
            if not chunk:
                break
            f.write(chunk)
            bytes_received += len(chunk)
    return bytes_received

# Every function above follows the same pattern:
#
#   1. get_ephemeral_port()  → open data listener
#   2. send_msg(ctrl_sock, command)
#   3. send_msg(ctrl_sock, ephemeral port number)
#   4. recv_msg(ctrl_sock)   → check "SUCCESS"/"FAILURE"
#   5. listen_sock.accept()  → server connects on data channel
#   6. transfer data using send_file_over_socket or recv_file_over_socket
#   7. recv_msg(ctrl_sock)   → read final status from server
#   8. print filename + bytes transferred
#
# do_ls() below has comments to know what to do
# for every step — use it as the template for
# do_get() and do_put().


def do_ls(ctrl_sock):
    """List files in the server's working directory."""

    listen_sock, eph_port = get_ephemeral_port()     # Step 1: open a free port for the incoming data connection


    send_msg(ctrl_sock, b"ls")     # Step 2: tell the server we want a directory listing


    
    send_msg(ctrl_sock, str(eph_port).encode()) # Step 3: tell the server which port to connect to for the data channel

    ack = recv_msg(ctrl_sock).decode().strip()
    
    if(str(ack)!= "SUCCESS ready for ls"):
        listen_sock.close()
        print(f"Server Error: {ack}") # Use print so the app doesn't crash        
        return

    listen_sock.settimeout(10)

    try:
       data_socket,address = listen_sock.accept()
    except ValueError as e:
        print("Type of error: ",type(e))
        print("Message: ",e)
    finally:
        listen_sock.close()
    bytes = recv_msg(data_socket).decode()
    data_socket.close()


    print(bytes)
    print(ack)

    


def do_get(ctrl_sock, filename: str):
    """Download <filename> from the server to the local machine."""
    listen_sock, eph_port = get_ephemeral_port()     # Step 1: open a free port for the incoming data connection
    send_msg(ctrl_sock, b"get "+filename.encode())     # Step 2: tell the server we want a directory listing
    send_msg(ctrl_sock, str(eph_port).encode()) # Step 3: tell the server which port to connect to for the data channel

    ack = recv_msg(ctrl_sock).decode().strip()
    
    if(str(ack)!= "SUCCESS ready for get"):
        listen_sock.close()
        print(f"Server Error: {ack}") # Use print so the app doesn't crash        
        return    
    listen_sock.settimeout(10)

    try:
       data_sock,address = listen_sock.accept()
    except ValueError as e:
        print("Type of error: ",type(e))
        print("Message: ",e)
    finally:
        listen_sock.close()

    bytes = recv_file_over_socket(data_sock, filename) 
    data_sock.close()

    print(f"{filename} received, {bytes} bytes transferred")




def do_put(ctrl_sock, filename: str):
    """Upload <filename> from the local machine to the server."""

    listen_sock, eph_port = get_ephemeral_port()     # Step 1: open a free port for the incoming data connection

    if(os.path.isfile(filename) == False):
        listen_sock.close()
        print(f"Server Error: file does not exist") # Use print so the app doesn't crash        
        return
    try:
        os.path.isfile(filename) == False
    except ValueError as e:
        print("Type of error: ",type(e))
        print("Message: ",e)

    send_msg(ctrl_sock,b"put "+filename.encode())
    send_msg(ctrl_sock, str(eph_port).encode()) # Step 3: tell the server which port to connect to for the data channel

    ack_bytes = recv_msg(ctrl_sock)
    ack = ack_bytes.decode().strip() # Convert bytes to a clean string
    if((ack)!= "SUCCESS ready for ls"):
        listen_sock.close()
        print(f"Server Error: {ack}") # Use print so the app doesn't crash        
        return
    
    listen_sock.settimeout(10)

    try:
       data_sock,address = listen_sock.accept()
    except listen_sock.timeout():
        print("timeout")
    finally:
        listen_sock.close()
    pass
    send_file_over_socket(data_sock,filename)

    bytes = recv_file_over_socket(data_sock, filename) 
    data_sock.close()

    print(f"{filename} received, {bytes} bytes transferred")


def main():
    """
    Entry point.

    TODO:
    1. Check sys.argv has exactly 3 items (script, server_name, port).
       If not, print usage and sys.exit(1).

    2. Create a TCP socket and connect to (server_name, server_port).
       Wrap in try/except — print a friendly error and exit on failure.

    3. Print "[CLIENT] Connected to <server>:<port>"

    4. Loop forever:
         - input("ftp> ").strip()
         - split into parts; parts[0].lower() is the command
         - "ls"   → do_ls(ctrl_sock)
         - "get"  → do_get(ctrl_sock, parts[1])  (check len(parts) >= 2)
         - "put"  → do_put(ctrl_sock, parts[1])  (check len(parts) >= 2)
         - "quit" → send_msg(ctrl_sock, b"quit")
                    recv_msg and print server's goodbye
                    break out of the loop
         - anything else → print unknown command message

    5. In a finally block: ctrl_sock.close()
       Print "[CLIENT] Disconnected."
    """
    if(len(sys.argv) < 2):
        print("Exiting")
        sys.exit(1)

    try:
        cntrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cntrl_sock.connect((sys.argv[1],int(sys.argv[2])))

    except ValueError as e:
        print("Type of error: ",type(e))
        print("Message: ",e)
    while(1):
        parts = input("ftp> ").strip().split()
        if(parts[0].lower() == "ls"):
            do_ls(cntrl_sock)
        elif(parts[0].lower() == "get" and len(parts) >=2):
            do_get(cntrl_sock,parts[1])
        elif(parts[0].lower() == "put" and len(parts) >=2):
            do_put(cntrl_sock,parts[1])
        elif(parts[0].lower() == "quit"):
            send_msg(cntrl_sock,b"quit")
            print("Client disconnected")
            exit()
        else:
            print("Message unkown please try again")






if __name__ == "__main__":
    main()
