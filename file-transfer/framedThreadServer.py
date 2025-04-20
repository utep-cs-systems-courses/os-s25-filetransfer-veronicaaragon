import socket
import threading
import os
import struct

HOST = "0.0.0.0"
PORT = 50001
SERVER_FILES_DIR = "server-files"

os.makedirs(SERVER_FILES_DIR, exist_ok=True)

def send_framed(sock, data: bytes):
    length = struct.pack("!I", len(data))
    sock.sendall(length + data)

def recv_all(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def recv_framed(sock):
    length_data = recv_all(sock, 4)
    if not length_data:
        return None
    length = struct.unpack("!I", length_data)[0]
    return recv_all(sock, length)

def handle_client(conn, addr):
    print(f"[+] Connection from {addr}")
    try:
        while True:
            data = recv_framed(conn)
            if not data:
                break

            command_parts = data.decode().strip().split()
            if not command_parts:
                continue

            cmd = command_parts[0]

            if cmd == "LIST":
                files = "\n".join(os.listdir(SERVER_FILES_DIR))
                send_framed(conn, files.encode())

            elif cmd == "GET" and len(command_parts) == 2:
                filename = command_parts[1]
                path = os.path.join(SERVER_FILES_DIR, filename)
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        send_framed(conn, f.read())
                else:
                    send_framed(conn, b"ERROR: File not found")

            elif cmd == "PUT" and len(command_parts) == 2:
                filename = command_parts[1]
                filedata = recv_framed(conn)
                with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                    f.write(filedata)
                send_framed(conn, b"Upload successful")

            else:
                send_framed(conn, b"Unknown or malformed command")
    finally:
        print(f"[-] Disconnected {addr}")
        conn.close()

def main():
    print(f"[*] Server listening on port {PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    main()
