#! /usr/bin/env python3

import os
import sys
import time

if os.fork() == 0:
    print(f"child {os.getpid()} sleeping");
    time.sleep(3)
    print("child exiting");
    sys.exit(1)

while True: 
    print("parent calling wait")
    waitResults = os.waitid(os.P_ALL, 0, os.WNOHANG | os.WEXITED)
    print(waitResults)
    time.sleep(1)

