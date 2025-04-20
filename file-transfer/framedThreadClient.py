import socket
import struct
import os

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12345 #9999 #8888

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

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_HOST, SERVER_PORT))
        print(f"[*] Connected to server at {SERVER_HOST}:{SERVER_PORT}")

        while True:
            cmd = input("Enter command (LIST, GET <file>, PUT <file>, QUIT): ").strip()
            if not cmd:
                continue

            tokens = cmd.split()
            if tokens[0].upper() == "QUIT":
                print("[-] Closing connection.")
                break

            elif tokens[0].upper() == "PUT" and len(tokens) == 2:
                filename = tokens[1]
                if not os.path.exists(filename):
                    print("File does not exist.")
                    continue
                send_framed(sock, cmd.encode())
                with open(filename, "rb") as f:
                    send_framed(sock, f.read())
                response = recv_framed(sock)
                print(response.decode())

            elif tokens[0].upper() == "GET" and len(tokens) == 2:
                send_framed(sock, cmd.encode())
                data = recv_framed(sock)
                if data.startswith(b"ERROR"):
                    print(data.decode())
                else:
                    with open(tokens[1], "wb") as f:
                        f.write(data)
                    print("File downloaded.")

            elif tokens[0].upper() == "LIST":
                send_framed(sock, cmd.encode())
                data = recv_framed(sock)
                print("Files on server:\n", data.decode())

            else:
                print("Unknown or malformed command.")

if __name__ == "__main__":
    main()