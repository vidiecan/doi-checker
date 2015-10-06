# coding=utf-8
import socks
import socket
import urllib2

"""
    Simple tor wrapper with changing IP addresses.
"""


class TorAuthException(Exception):
    pass


def new_identity(port, port_ctl, pwd=None, host="127.0.0.1"):
    """
        This is version/OS/configuration dependent.
        On windows the ports are 9150 and 9151, cookie auth. enabled by
        default and cookie token in control_auth_cookie.

        TOR must be started and the control_auth_cookie file must be 
        copied over with each restart! Setting no password was not working properly.

        The code snippet (taken from stackoverflow) has some issues with specific 
        cookies. In this case, restart Tor to generate new cookie.

        tor.new_identity(9150, 9151, open("control_auth_cookie", mode="r").read())

    """
    socks.setdefaultproxy()
    tor_c = socket.create_connection((host, port_ctl))
    if pwd is not None:
        s = 'AUTHENTICATE "{}"\r\nSIGNAL NEWNYM\r\n'.format(pwd)
        tor_c.send(s)
    else:
        tor_c.send('SIGNAL NEWNYM\r\n'.format(pwd))
    response = tor_c.recv(1024)
    if response != '250 OK\r\n250 OK\r\n':
        print 'Unexpected response from Tor control port: {}\n'.format(response)
        raise TorAuthException()
    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, host, port)
    old_socket = socket.socket
    socket.socket = socks.socksocket
    return old_socket


if __name__ == "__main__":
    new_identity(9150, 9151, open("control_auth_cookie", mode="r").read())
    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    url = "http://whatismyipaddress.com/"
    response = opener.open(url)
    print response.read()