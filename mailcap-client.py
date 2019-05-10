#!python3
import struct
import socket
import os
import sys
import mimetypes

s = socket.socket(socket.AF_UNIX)
s.connect(os.path.join(os.environ["HOME"], ".mailcap.sock"))

file = sys.argv[1]
mime = mimetypes.guess_type(file)[0]
data = open(file, "rb").read()

def strtr(x, c="B"):
    return struct.pack(c, len(x)) + x

s.sendall(strtr(file.encode('utf-8')) + strtr(mime.encode('utf-8')) + strtr(data, "!I"))
