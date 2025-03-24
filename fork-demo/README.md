# Hello motivational framing demo


helloServer.py
* listens on any:50001 for incoming TCP connection
* when a client connects, it,
** forks off a child to communicate with client who
*** sends "hello"
*** then pauses 1/4s,
*** then sends "world"


helloClient.py
* by default: connects to localhost:500001
* after connecting:
** if a delay of n is specified, it sleeps for n seconds (otherwise no sleep)
** repeatedly reads from the socket and prints what it rec'd, until EOF



