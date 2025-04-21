import socket
import struct
import os

SERVER_HOST = "localhost"
SERVER_PORT = 50000

def send_framed(sock, data: bytes): # send framed data to socket
    length = struct.pack("!I", len(data))
    sock.sendall(length + data) # 

def recv_all(sock, n): # read n bytes from socket
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def recv_framed(sock): # read framed data from socket
    length_data = recv_all(sock, 4)
    if not length_data:
        return None
    length = struct.unpack("!I", length_data)[0]
    return recv_all(sock, length)

def main(): # main function to handle client commands
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock: # create socket using IPv4 and TCP
        sock.connect((SERVER_HOST, SERVER_PORT)) #Connects to the server
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
                send_framed(sock, cmd.encode()) # send command to server
                with open(filename, "rb") as f: # open file in READ binary mode
                    send_framed(sock, f.read()) 
                response = recv_framed(sock)
                print(response.decode())

            elif tokens[0].upper() == "GET" and len(tokens) == 2:
                send_framed(sock, cmd.encode())
                data = recv_framed(sock) # receive data from server
                if data.startswith(b"ERROR"): 
                    print(data.decode())
                else:
                    with open(tokens[1], "wb") as f: # open file in WRITE binary mode
                        f.write(data)
                    print("File downloaded.")

            elif tokens[0].upper() == "LIST":
                send_framed(sock, cmd.encode())
                data = recv_framed(sock) #reads the framed response
                print("Files on server:\n", data.decode())
            else:
                print("Unknown or malformed command.")
if __name__ == "__main__":
    main()