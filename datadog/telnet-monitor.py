import socket
import select
import sys
import os
import re
import logging
import time
from datadog import initialize, statsd
from pygtail import Pygtail


class OpenvpnMonitor():

    def __init__(self, monitor_host, monitor_port, interval, datadog=True):
        self.host = monitor_host
        self.port = monitor_port
        self.interval = interval
        options = {"statsd_host": "127.0.0.1", "statsd_port": 8125}
        initialize(**options)
        self.s = None
        logging.basicConfig(level=logging.DEBUG)
        self.tags = ['server:{}'.format(os.uname()[1]),
                      'type:openvpn']

    def send_events(self, title, message, alert_type="info"):
        statsd.event(title, message, alert_type=alert_type, tags=self.tags)

    def connect(self):
        try:
            self.s = socket.create_connection((self.host, self.port), 2)
        except:
            print('Unable to connect')
            sys.exit()

    def disconnect(self):
        self.s.send('quit\n'.encode('ascii'))
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()

    def get_loadstats(self):
        self.s.send('load-stats\n'.encode('ascii'))
        return self.get_data()

    def get_status(self):
        self.s.send('status 2\n'.encode('ascii'))
        return self.get_data()

    def get_version(self):
        self.s.send('version\n'.encode('ascii'))
        return self.get_data()

    def get_data(self):
        socket_list = [self.s]
        read_sockets, write_sockets, error_sockets = select.select(socket_list, [], [])
        for sock in read_sockets:
            data = sock.recv(65565)
        return data.decode('utf8')

    def parse_version(self, version, datadog=True, elastic=False):
        """OpenVPN Version: OpenVPN 2.4.3 x86_64-redhat-linux-gnu [Fedora EPEL patched] [SSL (OpenSSL)] [LZO] [LZ4] [EPOLL] [PKCS11] [MH/PKTINFO] [AEAD] built on Jun 21 2017
OpenVPN Version: OpenVPN 2.3.14 x86_64-alpine-linux-musl [SSL (OpenSSL)] [LZO] [EPOLL] [MH] [IPv6] built on Dec 18 2016"""
        ver = version.split(" ")
        tags = ["version:{}_{}".format(ver[2], ver[3])]
        self.tags+=tags

    def parse_loadstats(self, loadstats):
        o_stats = None
        pattern = re.compile(r"SUCCESS:.*nclients=(?P<nclients>\d*),bytesin=(?P<bytesin>\d*),bytesout=(?P<bytesout>\d*).*")
        for line in loadstats.splitlines():
            o_stats = pattern.match(line)
        if o_stats:
            statsd.gauge('openvpn.nclients', o_stats.group('nclients'), tags=self.tags)
            statsd.gauge('openvpn.bytesin', o_stats.group('bytesin'), tags=self.tags)
            statsd.gauge('openvpn.bytesout', o_stats.group('bytesout'), tags=self.tags)

    def parse_status(self, status):
        """HEADER,CLIENT_LIST,Common Name,Real Address,Virtual Address,Bytes Received,Bytes Sent,Connected Since,Connected Since (time_t),Username
           HEADER,CLIENT_LIST,Common Name,Real Address,Virtual Address,Virtual IPv6 Address,Bytes Received,Bytes Sent,Connected Since,Connected Since (time_t),Username,Client ID,Peer ID
CLIENT_LIST,globbi,192.168.1.112:56513,10.8.0.18,,2735402,5955826,Sun Oct  1 20:15:18 2017,1506888918,jakobant,36,1"""
        COMMONNAME=1
        REAL_ADDR=2
        VIRT_ADDR=3
        BYTESIN=5 # 4
        BYTESOUT=6 # 5
        USERNAME=9 # 8
        CONN_SINCET=8 # 7
        for line in status.splitlines():
            if line.startswith('CLIENT_LIST'):
                o_stats = line.split(',')
                if len(o_stats) < 10:
                    BYTESIN = 4  # 4
                    BYTESOUT = 5  # 5
                    USERNAME = 8  # 8
                    CONN_SINCET = 7  # 7

                tags = ['commonname:{}'.format(o_stats[COMMONNAME]),
                        'real_addr:{}'.format(o_stats[REAL_ADDR].split(":")[0]),
                        'virt_addr:{}'.format(o_stats[VIRT_ADDR]),
                        'username:{}'.format(o_stats[USERNAME])] + self.tags
                connected_time = int(time.time()) - int(o_stats[CONN_SINCET])
                statsd.gauge('openvpn.client.bytesin', o_stats[BYTESIN], tags=tags)
                statsd.gauge('openvpn.client.bytesout', o_stats[BYTESOUT], tags=tags)
                statsd.gauge('openvpn.client.conntime', connected_time, tags=tags)

    def tail_log(self, logfile):
        """Fri Sep 29 21:29:59 2017 192.168.1.112:62493 TLS: Username/Password authentication succeeded for username 'jakobant'
Fri Sep 29 21:31:57 2017 192.168.1.112:62787 VERIFY OK: depth=1, C=IS, ST=Rkv, L=Reykjavik, O=Heima, OU=Ops, CN=Heima CA, name=EasyRSA, emailAddress=jakobant@gmail.com
Fri Sep 29 21:31:57 2017 192.168.1.112:62787 VERIFY OK: depth=0, C=IS, ST=Rkv, L=Reykjavik, O=Heima, OU=Ops, CN=globbi, name=EasyRSA, emailAddress=jakobant@gmail.com
AUTH-PAM: BACKGROUND: user 'jakobant' failed to authenticate: Authentication failure"""
        login = re.compile(r".*authentication succeeded.*")
        faild_login = re.compile(r".*(failed to authenticate|Incorrect password|was not found).*")
        for line in Pygtail(logfile):
            match = login.match(line)
            if match:
                print(line)
                self.send_events('Login success', line, alert_type='success')
            match = faild_login.match(line)
            if match:
                print(line)
                self.send_events('Authentication failure', line, alert_type='error')


if __name__ == "__main__":
    monitor = OpenvpnMonitor(os.getenv('MHOST', '127.0.0.1'), int(os.getenv('MPORT', '5555')), 60)
    while 1:
        monitor.connect()
        print(monitor.get_data())
        version = monitor.get_version()
        monitor.parse_version(version)
        loadstats = monitor.get_loadstats()
        monitor.parse_loadstats(loadstats)
        status = monitor.get_status()
        monitor.parse_status(status)
        monitor.disconnect()
        monitor.tail_log(os.getenv('OVPN_LOGS', '/var/log/openvpn.log'))
        time.sleep(60)

