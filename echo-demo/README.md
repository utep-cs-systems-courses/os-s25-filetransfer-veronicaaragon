# nets-tcp-framing

A simple tcp echo server & client

echoServer.py
* listens on any:50001 for incoming TCP connection
* echos any data sent to it.
* Connected socket is closed (and server terminates) after
** Socket is no longer readable
** And all rec'd data has been echoed
* parameters: ./echoServer.py -?
* Uses ../lib/params.h to parse parameters

echoClient.py
* by default: connects to localhost:500001
* sends "Hello world" and prints what comes back, twice.
* keeps reading (and printing what comes back) until connection closes
* parameters: ./echoClient -?
* Uses ../lib/params.h to parse parameters



