# mailcap-agent

`mailcap-agent` can be used to use local commands to view files from a remote
host, e.g. when using ssh to read email. To use it, run

    ./mailcap-server.py ~/.mailcap.sock

on your local host, then add something like this to your `~/.ssh/config`:

    Host example.com
        RemoteForward /home/remoteuser/.mailcap.sock /home/localuser/.mailcap.sock

On the remote host, set up your `~/.mailcap`, e.g. to open all images and PDFs
using mailcap-agent:

    image/*;~/mailcap-client.py %s %t
    application/pdf;~/mailcap-client.py %s %t

and try opening a file.

