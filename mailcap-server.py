#!python3
import struct
import socket
import os
import tempfile
import mailcap
import sys
import argparse
import daemon

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
    
        def recv_exact(self, length):
            retval = bytes()
            while len(retval) < length:
                data = self.recv(length - len(retval))
                if len(data) == 0:
                    return None
                retval += data
            return retval

    def __init__(self, path="mailcap.sock"):
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(path)
        self._socket.listen(3)
        self._dir = tempfile.TemporaryDirectory()

    def close(self):
        self._socket.close()
        self._dir.cleanup()

    def next_file(self, initial_timeout=None, timeout=5):
        conn = self.Connection(self._socket.accept()[0])
        conn.timeout(initial_timeout)

        data = conn.recv_exact(1)
        if data is None:
            return None
        fn_len = struct.unpack("B", data)[0]

        conn.timeout(timeout)
        
        data = conn.recv_exact(fn_len)
        if data is None:
            return None
        fn = data.decode('utf-8')
        fn = fn.replace("/", "_")
        if len(fn) == 0 or fn in ['.', '..']:
            return None
        
        data = conn.recv_exact(1)
        if data is None:
            return None
        mime_len = struct.unpack("B", data)[0]
        
        data = conn.recv_exact(mime_len)
        if data is None:
            return None
        mime = data.decode('utf-8')

        data = conn.recv_exact(4)
        if data is None:
            return None
        file_len = struct.unpack("!I", data)[0]

        print(fn, mime)
        
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', '-p', default=os.path.join(os.environ['HOME'], '.mailcap.pid'))
    parser.add_argument('--action', '-a', default='run', choices=['run', 'kill'])
    parser.add_argument('--no-daemonize', '-n', action='store_true')
    parser.add_argument('--socket', '-s', default=os.path.join(os.environ['HOME'], '.mailcap.sock'))
    args = parser.parse_args()

    if args.action == 'kill':
        if os.path.exists(args.socket):
            os.remove(args.socket)
        if os.path.exists(args.pid):
            pid = int(open(args.pid).read())
            try:
                os.kill(pid, 3)
            except ProcessLookupError as e:
                print("Failed to kill process with pid %d:" % (pid,), str(e))
            os.remove(args.pid)
            if os.path.exists(args.socket):
                os.remove(args.socket)
    elif args.action == 'run':
        if os.path.exists(args.pid):
            print("Already running with pid %d" % (int(open(args.pid).read()),))
            exit()
        if os.path.exists(args.socket):
            os.remove(args.socket)

        with daemon.DaemonContext(detach_process=not args.no_daemonize, files_preserve=[1,2]):
            sv = Server(args.socket)
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
                        if 'nodelete' not in match[1]:
                            os.remove(f)
