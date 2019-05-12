# mailcap-agent

`mailcap-agent` can be used to use local commands to view files from a remote
host, e.g. when using ssh to read email. To use it, run

    mailcap-server.py

on your local host, then add something like this to your `~/.ssh/config`:

    Host example.com
        RemoteForward /home/remoteuser/.mailcap.sock /home/localuser/.mailcap.sock

On the remote host, set up your `~/.mailcap`, e.g. to open all images and PDFs
using mailcap-agent, use the following example. The `%t` in these invocations
is replaced with the type. It is optional, and the default is to run `file(1)`
on the file and get the type from that.

    image/*;mailcap-client.py %s %t
    application/pdf;mailcap-client.py %s %t

Now try opening a file, either with some application that uses your mailcap
file or directly:

    mailcap-client.py some_image.jpg image/jpeg

or

    mailcap-client.py invoice.pdf
