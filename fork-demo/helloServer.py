#! /usr/bin/env python3

# Echo server program

import socket, sys, re, os, time
sys.path.append("../lib")       # for params
import params

switchesVarDefaults = (
    (('-l', '--listenPort') ,'listenPort', 50001),
    (('-?', '--usage'), "usage", False), # boolean (set if present)
    )


paramMap = params.parseParams(switchesVarDefaults)

listenPort = paramMap['listenPort']
listenAddr = ''       # Symbolic name meaning all available interfaces

pidAddr = {}                    # for active connections: maps pid->client addr 

if paramMap['usage']:
    params.usage()

# server code to be run by child
def chatWithClient(connAddr):  
    sock, addr = connAddr
    print(f'Child: pid={os.getpid()} connected to client at {addr}')
    sock.send(b"hello")
    time.sleep(0.25);       # delay 1/4s
    sock.send(b"world")
    sock.shutdown(socket.SHUT_WR)
    sys.exit(0)                 # terminate child

listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# listener socket will unbind immediately on close
listenSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# accept will block for no more than 5s
listenSock.settimeout(5)          
# bind listener socket to port
listenSock.bind((listenAddr, listenPort))
# set state to listen
listenSock.listen(1)              # allow only one outstanding request

# s is a factory for connected sockets


while True:
    # reap zombie children (if any)
    while pidAddr.keys():
        # Check for exited children (zombies).  If none, don't block (hang)
        if (waitResult := os.waitid(os.P_ALL, 0, os.WNOHANG | os.WEXITED)): 
            zPid, zStatus = waitResult.si_pid, waitResult.si_status
            print(f"""zombie reaped:
            \tpid={zPid}, status={zStatus}
            \twas connected to {pidAddr[zPid]}""")
            del pidAddr[zPid]
        else:
            break               # no zombies; break from loop
    print(f"Currently {len(pidAddr.keys())} clients")

    try:
        connSockAddr = listenSock.accept() # accept connection from a new client
    except TimeoutError:
        connSockAddr = None 

    if connSockAddr is None:
        continue
        
    forkResult = os.fork()     # fork child for this client 
    if (forkResult == 0):        # child
        listenSock.close()         # child doesn't need listenSock
        chatWithClient(connSockAddr)
    # parent
    sock, addr = connSockAddr
    sock.close()   # parent closes its connection to client
    pidAddr[forkResult] = addr
    print(f"spawned off child with pid = {forkResult} at addr {addr}")
    

