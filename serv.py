#!/usr/bin/env python3

import socket
import os
import sys
import subprocess

HEADER_SIZE = 10
CHUNK_SIZE = 4096


def send_all(sock, data: bytes):
    # sends all bytes (send() might not send everything at once)
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise RuntimeError("Socket connection broken during send")
        total_sent += sent


def recv_exact(sock, n: int) -> bytes:
    # makes sure we receive exactly n bytes
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RuntimeError("Socket closed early")
        buf += chunk
    return buf


def send_msg(sock, payload: bytes):
    # send message with 10-byte header
    header = str(len(payload)).zfill(HEADER_SIZE).encode()
    send_all(sock, header + payload)


def recv_msg(sock) -> bytes:
    # read header first, then payload
    raw_header = recv_exact(sock, HEADER_SIZE)
    payload_len = int(raw_header.decode().strip())
    return recv_exact(sock, payload_len)


def connect_data_socket(client_ip: str, client_port: int):
    # connect back to client on ephemeral port
    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_sock.connect((client_ip, client_port))
    return data_sock


def handle_ls(ctrl_sock, client_ip: str, data_port: int):
    # handles ls command
    try:
        send_msg(ctrl_sock, b"SUCCESS ready for ls")

        data_sock = connect_data_socket(client_ip, data_port)
        try:
            result = subprocess.run(["ls", "-l"], capture_output=True, text=True)
            listing = result.stdout if result.stdout else result.stderr
            send_msg(data_sock, listing.encode())
        finally:
            data_sock.close()

        send_msg(ctrl_sock, b"SUCCESS ls complete")

    except Exception as e:
        try:
            send_msg(ctrl_sock, f"FAILURE ls failed: {e}".encode())
        except:
            pass


# =========================
# TODO: COMPLETE BELOW
# =========================

def handle_get(ctrl_sock, client_ip: str, data_port: int, filename: str):
    # TODO:
    # 1. check if file exists (os.path.isfile)
    # 2. send SUCCESS or FAILURE
    # 3. connect to data socket
    # 4. send file using chunks
    # 5. close socket
    # 6. send final SUCCESS with byte count
    pass


def handle_put(ctrl_sock, client_ip: str, data_port: int, filename: str):
    # TODO:
    # 1. send SUCCESS ready
    # 2. connect to data socket
    # 3. receive file (read header, then chunks)
    # 4. save file
    # 5. close socket
    # 6. send final SUCCESS with byte count
    pass


def handle_client(ctrl_sock, client_addr):
    client_ip = client_addr[0]

    while True:
        try:
            raw_command = recv_msg(ctrl_sock)
        except:
            break

        command_line = raw_command.decode().strip()
        if not command_line:
            send_msg(ctrl_sock, b"FAILURE empty command")
            continue

        parts = command_line.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd == "quit":
            send_msg(ctrl_sock, b"SUCCESS goodbye")
            break

        # TODO:
        # receive data port from client using recv_msg
        # convert to int
        # store as data_port

        if cmd == "ls":
            # TODO: call handle_ls(ctrl_sock, client_ip, data_port)
            pass

        elif cmd == "get":
            # TODO: check filename exists in parts
            # then call handle_get(...)
            pass

        elif cmd == "put":
            # TODO: check filename exists in parts
            # then call handle_put(...)
            pass

        else:
            send_msg(ctrl_sock, f"FAILURE unknown command: {cmd}".encode())


def main():
    # TODO:
    # 1. check sys.argv length
    # 2. convert port to int
    # 3. create socket
    # 4. bind + listen
    # 5. accept clients in loop
    # 6. call handle_client
    # 7. close sockets properly
    pass


if __name__ == "__main__":
    main()
