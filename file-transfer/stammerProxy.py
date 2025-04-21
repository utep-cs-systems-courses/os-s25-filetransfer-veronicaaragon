#!/usr/bin/env python3
import sys
import traceback
from select import *
from socket import *
import time
import random #Imports necessary modules for networking, error handling, and random behavior

import re

sys.path.append("../lib")       # for params
import params # Adds the parent's lib directory to Python's path to import the params module

switchesVarDefaults = ( #Defines command-line parameters with their default values
    (('-l', '--listenPort') ,'listenPort', 50000),
    (('-s', '--server'), 'server', "127.0.0.1:50001"),
    (('-d', '--debug'), "debug", False), # boolean (set if present)
    (('-?', '--usage'), "usage", False), # boolean (set if present)
    (('-p', '--pausedelay'), 'pauseDelay', 0.5)
    ) # proxy listens on port 50000 by default and forwards to 127.0.0.1:50001

#Parses command-line arguments according to the defined switches
progname = "stammerProxy"
paramMap = params.parseParams(switchesVarDefaults)
#Extracts parameters from the parsed command-line arguments
server, listenPort, usage, debug, pauseDelay = paramMap["server"], paramMap["listenPort"], paramMap["usage"], paramMap["debug"], float(paramMap["pauseDelay"])

if usage: # Shows usage information if requested.
    params.usage()

try: #Parses the server address and ports, exiting with an error if they are invalid
    serverHost, serverPort = re.split(":", server)
    serverPort = int(serverPort)
except:
    print("Can't parse server:port from '%s'" % server)
    sys.exit(1)

try:
    listenPort = int(listenPort)
except:
    print("Can't parse listen port from %s" % listenPort)
    sys.exit(1)

print ("%s: listening on %s, will forward to %s\n" % 
       (progname, listenPort, server)) #Displays the proxy's configuration

#Initializes global variables to track sockets and connections
sockNames = {}               # from socket to name
nextConnectionNumber = 0     # each connection is assigned a unique id
now = time.time()

#class to handle forwarding data between sockets
class Fwd: #Each forwarder instance has: input/output socket, buffer & delay settings
    def __init__(self, conn, inSock, outSock, bufCap = 1000):
        global now
        self.conn, self.inSock, self.outSock, self.bufCap = conn, inSock, outSock, bufCap
        self.inClosed, self.buf = 0, bytes(0)
        self.delaySendUntil = 0 # no delay
    def checkRead(self): #determine if a socket should be monitored for reading or writing
        if len(self.buf) < self.bufCap and not self.inClosed:
            return self.inSock
        else: #Only reads if the buffer has space and the input socket is open
            return None
    def checkWrite(self):
        if len(self.buf) > 0 and now >= self.delaySendUntil:
            return self.outSock
        else:#Only writes if there's data in the buffer and any configured delay has expired
            return None
    def doRecv(self): #Receive data from input socket & add it in to buffer
        try:
            b = self.inSock.recv(self.bufCap - len(self.buf))
        except:
            self.conn.die()
            return
        if len(b):
            self.buf += b
        else:
            self.inClosed = 1
        self.checkDone() #Marks the input as closed if no data is received (EOF)
    def doSend(self): #simulates network conditions that break up messages into unpredictable chunks
        global now
        try: #sends a random portion of the buffer rather than all at once
            bufLen = len(self.buf)
            toSend = random.randrange(1, bufLen+1)
            if debug: print("attempting to send %d of %d" % (toSend, len(self.buf)))
            n = self.outSock.send(self.buf[0:toSend])
            self.buf = self.buf[n:]
            if len(self.buf): #After sending, it adds a delay before the next send operation
                self.delaySendUntil = now + pauseDelay
        except Exception as e:
            print(e)
            self.conn.die()
        self.checkDone()
        
    def checkDone(self): #Checks if forwarding is complete (buffer empty and input closed)
        if len(self.buf) == 0 and self.inClosed:
            self.outSock.shutdown(SHUT_WR)
            self.conn.fwdDone(self) #If done, it signals end of transmission & notifies connection
            
    
connections = set() #track all active connections

class Conn: #Handles a connection between a client and server
    def __init__(self, csock, caddr, af, socktype, saddr):
        global nextConnectionNumber #connection has a unique index, client/server socket & forwarders
        self.csock = csock      # to client
        self.caddr, self.saddr = caddr, saddr # addresses
        self.connIndex = connIndex = nextConnectionNumber
        nextConnectionNumber += 1
        self.ssock = ssock = socket(af, socktype)
        self.forwarders = forwarders = set()
        print("New connection #%d from %s" % (connIndex, repr(caddr)))
        sockNames[csock] = "C%d:ToClient" % connIndex #Assigns names to sockets for debugging purposes
        sockNames[ssock] = "C%d:ToServer" % connIndex
        ssock.setblocking(False) #Sets up a non-blocking connection to destination server
        ssock.connect_ex(saddr)
        forwarders.add(Fwd(self, csock, ssock)) #Creates two forwarders:one from client to server
        forwarders.add(Fwd(self, ssock, csock))#and one from server to client
        connections.add(self)
        
    def fwdDone(self, forwarder): #Removes a completed forwarder
        forwarders = self.forwarders
        forwarders.remove(forwarder)
        print("forwarder %s ==> %s from connection %d shutting down" % (sockNames[forwarder.inSock], sockNames[forwarder.outSock], self.connIndex))
        if len(forwarders) == 0:
            self.die() #If all forwarders are done, terminates the connection
            
    def die(self): #Cleans up a connection by closing sockets and removing references
        print("connection %d shutting down" % self.connIndex)
        for s in self.ssock, self.csock:
            del sockNames[s]
            try:
                s.close()
            except:
                pass 
        connections.remove(self)
        
    def doErr(self): #Cleans up a connection by closing sockets and removing references
        print("forwarder from client %s failing due to error" % repr(self.caddr))
        die()
                
class Listener: #Listens for incoming connections and creates a new connection object for each
    def __init__(self, bindaddr, saddr, addrFamily=AF_INET, socktype=SOCK_STREAM): # saddr is address of server
        self.bindaddr, self.saddr = bindaddr, saddr
        self.addrFamily, self.socktype = addrFamily, socktype
        self.lsock = lsock = socket(addrFamily, socktype)
        sockNames[lsock] = "listener"
        lsock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        lsock.bind(bindaddr)
        lsock.setblocking(False) #non-blocking socket with address reuse enabled
        lsock.listen(2)
    def doRecv(self): #Accepts new client connection & creates a Conn object to handle it
        try:
            csock, caddr = self.lsock.accept() # socket connected to client
            conn = Conn(csock, caddr, self.addrFamily, self.socktype, self.saddr)
        except:
            print("weird.  listener readable but can't accept!")
            traceback.print_exc(file=sys.stdout)
            
    def doErr(self):#Handles errors with the listener socket by exiting the program
        print("listener socket failed!!!!!")
        sys.exit(2)
# Methods to indicate which socket should be monitored for reading, writing, and errors
    def checkRead(self):
        return self.lsock
    def checkWrite(self):
        return None
    def checkErr(self):
        return self.lsock
        
#Creates a listener that forwards connections to the target server
l = Listener(("0.0.0.0", listenPort), (serverHost, serverPort))
#Helper function to convert socket objects to their names for debugging
def lookupSocknames(socks):
    return [ sockName(s) for s in socks ]

while 1: #Main event loop that sets up maps for select() to monitor socket activity
    rmap,wmap,xmap = {},{},{}   # socket:object mappings for select
    xmap[l.checkErr()] = l #listener is monitored for both reading and errors
    rmap[l.checkRead()] = l
    now = time.time()
    nextDelayUntil = now + 10   # default 10s poll
    for conn in connections: #Iterates through all active connections to check their status
        for sock in conn.csock, conn.ssock:
            xmap[sock] = conn
            for fwd in conn.forwarders: #Calculates next send delay to optimize the select() timeout
                sock = fwd.checkRead()
                if (sock): rmap[sock] = fwd
                sock = fwd.checkWrite()
                if (sock): wmap[sock] = fwd
                delayUntil = fwd.delaySendUntil
                if (delayUntil < nextDelayUntil and delayUntil > now): # minimum active delay
                    nextDelayUntil = delayUntil
    maxSleep = nextDelayUntil - now #Uses select() to efficiently wait for socket activity or until the next delay expires
    if debug: print("select max sleep=%fs" % maxSleep)
    rset, wset, xset = select(list(rmap.keys()), list(wmap.keys()), list(xmap.keys()), maxSleep)
    if debug: print([ repr([ sockNames[s] for s in sset]) for sset in [rset,wset,xset] ])
    for sock in rset: #Handles ready sockets by calling the appropriate methods on their associated objects
        rmap[sock].doRecv()
    for sock in wset:
        wmap[sock].doSend()
    for sock in xset:
        xmap[sock].doErr()