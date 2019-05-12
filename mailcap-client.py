#!/usr/bin/python3
import struct
import socket
import os
import sys
import mimetypes
import subprocess
import hashlib

s = socket.socket(socket.AF_UNIX)
s.connect(os.path.join(os.environ["HOME"], ".mailcap.sock"))

filename = sys.argv[1]
if len(sys.argv) > 2:
    mime = sys.argv[2]
else:
    mime = subprocess.run(["file", "-i", "-b", filename], check=True, stdout=subprocess.PIPE).stdout.decode('utf-8')
data = open(filename, "rb").read()

def strtr(x, c="B"):
    return struct.pack(c, len(x)) + x

hash = hashlib.sha256()
hash.update(data)

s.sendall(strtr(filename.split(os.pathsep)[-1].encode('utf-8')) + strtr(mime.encode('utf-8')) + hash.digest())

response = s.recv(1)
if len(response) and response[0] == 1:
    s.sendall(strtr(data, "!I"))
