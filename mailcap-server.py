#!python3
import struct
import socket
import os
import tempfile
import mailcap
import sys
import argparse
import daemon
import hashlib

sockpath = "mailcap.sock"

if os.path.exists(sockpath):
    os.remove(sockpath)

class Server(object):
    class Connection(object):
        def __init__(self, conn):
            self._conn = conn
    
        def timeout(self, timeout):
            return self._conn.settimeout(timeout)

        def close(self):
            self._conn.close()

        def recv(self, size):
            data = self._conn.recv(size)
            return data

        def send(self, data):
            return self._conn.send(data)
    
        def recv_exact(self, length):
            retval = bytes()
            while len(retval) < length:
                data = self.recv(length - len(retval))
                if len(data) == 0:
                    return None
                retval += data
            return retval

    def __init__(self, path="mailcap.sock", dir = None):
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(path)
        self._socket.listen(3)
        if dir:
            if not os.path.exists(dir):
                os.makedirs(dir)
            self._dir = dir
        else:
            self._dir = tempfile.TemporaryDirectory()

    def close(self):
        self._socket.close()
        self._dir.cleanup()

    def next_file(self, initial_timeout=None, timeout=5):
        conn = self.Connection(self._socket.accept()[0])
        conn.timeout(initial_timeout)

        # Receive filename length
        data = conn.recv_exact(1)
        if data is None:
            return None
        fn_len = struct.unpack("B", data)[0]

        conn.timeout(timeout)
        
        # Receive filename
        data = conn.recv_exact(fn_len)
        if data is None:
            return None
        fn = data.decode('utf-8')

        # Strip the filename of /, do sanity checks
        fn = fn.replace("/", "_")
        if len(fn) == 0 or fn in ['.', '..']:
            s.close()
            return None

        # Receive the mime type length
        data = conn.recv_exact(1)
        if data is None:
            return None
        mime_len = struct.unpack("B", data)[0]
        
        # Receive the mime type
        data = conn.recv_exact(mime_len)
        if data is None:
            return None
        mime = data.decode('utf-8')

        # Receive the SHA256 hash
        data = conn.recv_exact(hashlib.sha256().digest_size)
        if data is None:
            return None

        full_name = os.path.join(self._dir.name, fn)
        append = 0
        # While the filename already exists, check if we have a hash match
        while os.path.exists(full_name):
            hash = hashlib.sha256()
            hash.update(open(full_name, "rb").read())
            
            # Found a matching file. Do not receive the file.
            if data == hash.digest():
                conn.send(b'\x00')
                conn.close()
                return full_name, mime

            append += 1
            hash = hashlib.sha256()
            name_parts = fn.split('.')
            if len(name_parts) > 1:
                full_name = os.path.join(self._dir.name, "%s-%d.%s" % ('.'.join(name_parts[:-1]), append, name_parts[-1]))
            else:
                full_name = os.path.join(self._dir.name, "%s-%d" % (fn, append, name_parts[-1]))
        conn.send(b'\x01')

        # Receive the file length
        data = conn.recv_exact(4)
        if data is None:
            return None
        file_len = struct.unpack("!I", data)[0]

        # Receive the file data
        fn = os.path.join(self._dir.name, fn)
        with open(fn, "wb+") as f:
            while file_len > 0:
                data = conn.recv(min(4096, file_len))
                f.write(data)
                file_len -= len(data)

        conn.close()

        if file_len is 0:
            return fn, mime
        else:
            os.remove(fn)
            return None

def run_server(args):
    sv = Server(path=args.socket, dir=args.dir)
    caps = mailcap.getcaps()
    open(args.pid, "w+").write(str(os.getpid()))
    while True:
        rv = sv.next_file()
        if rv:
            f, mime = rv
            print(f, mime)
            match = mailcap.findmatch(caps, mime.split(';')[0], filename=f)
            if match and match[0]:
                os.system(match[0])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', '-p', default=os.path.join(os.environ['HOME'], '.mailcap.pid'))
    parser.add_argument('--action', '-a', default='run', choices=['run', 'kill'])
    parser.add_argument('--no-daemonize', '-n', action='store_true')
    parser.add_argument('--socket', '-s', default=os.path.join(os.environ['HOME'], '.mailcap.sock'))
    parser.add_argument('--dir', '-d', default=None)
    parser.add_argument('--force', '-f', action='store_true')
    args = parser.parse_args()

    if args.action == 'kill' or args.force:
        if os.path.exists(args.socket):
            os.remove(args.socket)
        if os.path.exists(args.pid):
            pid = int(open(args.pid).read())
            try:
                os.kill(pid, 3)
            except ProcessLookupError as e:
                if not args.force:
                    print("Failed to kill process with pid %d:" % (pid,), str(e))
            os.remove(args.pid)
            if os.path.exists(args.socket):
                os.remove(args.socket)
    if args.action == 'run':
        if os.path.exists(args.pid):
            print("Already running with pid %d" % (int(open(args.pid).read()),))
            exit()
        if os.path.exists(args.socket):
            os.remove(args.socket)

        if args.no_daemonize:
            run_server(args)
        else:
            with daemon.DaemonContext():
                run_server(args)
