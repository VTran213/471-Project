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


def handle_get(ctrl_sock, client_ip: str, data_port: int, filename: str):
    """Send a file from server to client over the data channel."""
    if not os.path.isfile(filename):
        send_msg(ctrl_sock, f"FAILURE file not found: {filename}".encode())
        return

    try:
        send_msg(ctrl_sock, b"SUCCESS ready for get")

        data_sock = connect_data_socket(client_ip, data_port)
        try:
            file_bytes = b""
            with open(filename, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    file_bytes += chunk

            byte_count = len(file_bytes)
            send_msg(data_sock, file_bytes)

        finally:
            data_sock.close()

        send_msg(ctrl_sock, f"SUCCESS get complete: {filename} {byte_count} bytes".encode())
        print(f"GET: sent {filename} ({byte_count} bytes)")

    except Exception as e:
        try:
            send_msg(ctrl_sock, f"FAILURE get failed: {e}".encode())
        except:
            pass
 
 
def handle_put(ctrl_sock, client_ip: str, data_port: int, filename: str):
    """Receive a file from client and save it on the server."""
    try:
        send_msg(ctrl_sock, b"SUCCESS ready for put")

        data_sock = connect_data_socket(client_ip, data_port)
        try:
            file_data = recv_msg(data_sock)
        finally:
            data_sock.close()

        with open(filename, "wb") as f:
            f.write(file_data)

        byte_count = len(file_data)
        send_msg(ctrl_sock, f"SUCCESS put complete: {filename} {byte_count} bytes".encode())
        print(f"PUT: received {filename} ({byte_count} bytes)")

    except Exception as e:
        try:
            send_msg(ctrl_sock, f"FAILURE put failed: {e}".encode())
        except:
            pass
 
 
def handle_client(ctrl_sock, client_addr):
    """Main loop for a single client session over the control channel."""
    client_ip = client_addr[0]
    print(f"Session started with {client_ip}:{client_addr[1]}")

    while True:
        try:
            raw_command = recv_msg(ctrl_sock)
        except Exception:
            print(f"Client {client_ip} disconnected unexpectedly")
            break

        command_line = raw_command.decode().strip()
        if not command_line:
            send_msg(ctrl_sock, b"FAILURE empty command")
            continue

        parts = command_line.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd == "quit":
            send_msg(ctrl_sock, b"SUCCESS goodbye")
            print(f"Client {client_ip} quit cleanly")
            break

        try:
            data_port = int(recv_msg(ctrl_sock).decode().strip())
        except Exception as e:
            send_msg(ctrl_sock, f"FAILURE could not read data port: {e}".encode())
            continue

        if cmd == "ls":
            handle_ls(ctrl_sock, client_ip, data_port)

        elif cmd == "get":
            if len(parts) < 2 or not parts[1].strip():
                send_msg(ctrl_sock, b"FAILURE get requires a filename")
            else:
                handle_get(ctrl_sock, client_ip, data_port, parts[1].strip())

        elif cmd == "put":
            if len(parts) < 2 or not parts[1].strip():
                send_msg(ctrl_sock, b"FAILURE put requires a filename")
            else:
                handle_put(ctrl_sock, client_ip, data_port, parts[1].strip())

        else:
            send_msg(ctrl_sock, f"FAILURE unknown command: {cmd}".encode())
 
 
def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <port>")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Error: port must be an integer")
        sys.exit(1)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR prevents "address already in use" when restarting server quickly
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("", port))
    server_socket.listen(5)
    print(f"FTP server ready on port {port}")

    try:
        while True:
            try:
                ctrl_sock, client_addr = server_socket.accept()
            except KeyboardInterrupt:
                print("\nShutting down server...")
                break

            try:
                handle_client(ctrl_sock, client_addr)
            except Exception as e:
                print(f"Unhandled error with client {client_addr}: {e}")
            finally:
                ctrl_sock.close()

    finally:
        server_socket.close()
        print("Server closed.")
 
 
if __name__ == "__main__":
    main()
 