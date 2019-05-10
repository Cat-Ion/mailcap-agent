#!/usr/bin/python3
import struct
import socket
import os
import sys
import mimetypes
import subprocess

s = socket.socket(socket.AF_UNIX)
s.connect(os.path.join(os.environ["HOME"], ".mailcap.sock"))

filename = sys.argv[1]
mime = subprocess.run(["file", "-i", "-b", filename], check=True, stdout=subprocess.PIPE).stdout.decode('utf-8')
data = open(filename, "rb").read()

def strtr(x, c="B"):
    return struct.pack(c, len(x)) + x

s.sendall(strtr(filename.encode('utf-8')) + strtr(mime.encode('utf-8')) + strtr(data, "!I"))
