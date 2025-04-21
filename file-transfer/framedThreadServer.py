import socket
import threading
import os
import struct

HOST = "0.0.0.0"
PORT = 50001
SERVER_FILES_DIR = "server-files"
os.makedirs(SERVER_FILES_DIR, exist_ok=True)

# accurately reconstruct complete messages regardless of how they're fragmented
def send_framed(sock, data: bytes): 
    length = struct.pack("!I", len(data)) # standard network byte order
    sock.sendall(length + data) # tells receiver exactly how many bytes to expect

def recv_all(sock, n): #collects all the pieces until it has the complete message
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data)) # remaining number of bytes we still need
        if not packet:
            return None
        data.extend(packet) # adds the newly received bytes to the existing data
    return bytes(data)

def recv_framed(sock): # receives the length header and then the message
    length_data = recv_all(sock, 4) #first reading the 4-byte length header
    if not length_data:
        return None
    length = struct.unpack("!I", length_data)[0] #uses length to read the exact # of bytes message
    return recv_all(sock, length)

def handle_client(conn, addr):
    print(f"[+] Connection from {addr}")
    try:
        while True:
            data = recv_framed(conn) #receives the length header and then the message
            if not data:
                break
            # Decode the data and split it into command and arguments
            command_parts = data.decode().strip().split()
            if not command_parts:
                continue

            cmd = command_parts[0] #first part is the command

            if cmd == "LIST": #get all filenames in its storage directory
                files = "\n".join(os.listdir(SERVER_FILES_DIR)) # Joins them into a single string with newlines as separators
                send_framed(conn, files.encode()) #Encodes this string into bytes and sends it back framed

            elif cmd == "GET" and len(command_parts) == 2: #client wants to download a file
                filename = command_parts[1] 
                path = os.path.join(SERVER_FILES_DIR, filename) 
                if os.path.exists(path): #check if the file exists
                    with open(path, "rb") as f:
                        send_framed(conn, f.read()) # Reads the file and sends it back framed
                else:
                    send_framed(conn, b"ERROR: File not found")

            elif cmd == "PUT" and len(command_parts) == 2: #client wants to upload a file
                filename = command_parts[1]
                filedata = recv_framed(conn) # Receives the file data
                with open(os.path.join(SERVER_FILES_DIR, filename), "wb") as f:
                    f.write(filedata) # Writes the received data to a file
                send_framed(conn, b"Upload successful")

            else:
                send_framed(conn, b"Unknown or malformed command")
    finally:
        print(f"[-] Disconnected {addr}") # Close the connection
        conn.close()

def main():
    print(f"[*] Server listening on port {PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT)) # Bind the socket to the host and port
        s.listen() # Listen for incoming connections
        while True:
            conn, addr = s.accept() # Accept a new connection
            thread = threading.Thread(target=handle_client, args=(conn, addr)) # Create a new thread for each client
            thread.start() # Start the thread to handle the client

if __name__ == "__main__":
    main()
