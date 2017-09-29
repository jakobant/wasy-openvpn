#!env python
import socket
import select
import sys
import os
import re
import logging
import time
from datadog import initialize
from datadog import ThreadStats
from pygtail import Pygtail

options = {
    'api_key': os.getenv('DD_API_KEY'),
    'app_key': os.getenv('DD_APP_KEY')
}
initialize(**options)
logging.basicConfig(level=logging.DEBUG)
global_tags = ['server:{}'.format(os.uname()[1]),
               'type:openvpn']

# main function

class OpenvpnMonitor():

    def __init__(self, monitor_host, monitor_port, interval, datadog=True, elstic=False):
        self.host = monitor_host
        self.port = monitor_port
        self.interval = interval
        self.s = None
        self.datadog = datadog
        self.stats = ThreadStats()
        self.stats.start(flush_interval=interval)

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(2)
        try:
            self.s.connect((self.host, self.port))
        except:
            print('Unable to connect')
            sys.exit()

    def disconnect(self):
        self.s.close()

    def get_loadstats(self):
        self.s.send('load-stats\n'.encode('ascii'))
        return self.get_data()

    def get_status(self):
        self.s.send('status 3\n'.encode('ascii'))
        return self.get_data()

    def get_data(self):
        socket_list = [sys.stdin, self.s]
        read_sockets, write_sockets, error_sockets = select.select(socket_list, [], [])
        for sock in read_sockets:
            data = sock.recv(16384)
        return data.decode('utf8')

    def parse_loadstats(self, loadstats, datadog=True, elastic=False):
        pattern = re.compile(r"SUCCESS:.*nclients=(?P<nclients>\d*),bytesin=(?P<bytesin>\d*),bytesout=(?P<bytesout>\d*).*")
        for line in loadstats.splitlines():
            o_stats = pattern.match(line)
        if o_stats:
            if self.datadog:
                self.stats.gauge('openvpn.nclients', o_stats.group('nclients'))
                self.stats.gauge('openvpn.bytesin', o_stats.group('bytesin'))
                self.stats.gauge('openvpn.bytesout', o_stats.group('bytesout'))

    def parse_status(self, status):
        pattern = re.compile(r"CLIENT_LIST\t(?P<commonname>.*)\t(?P<real_address>.*)\t(?P<virt_address>.*)\t(?P<bytesout>.*)\t(?P<bytesin>.*)\t(?P<connected_since>.*)\t(?P<connect_sincet>.*)\t(?P<username>.*).*")
        for line in status.splitlines():
            o_stats = pattern.match(line)
            if o_stats:
                if self.datadog:
                    tags = ['commonname:{}'.format(o_stats.group('commonname')),
                            'real_addr:{}'.format(o_stats.group('real_address').split(":")[0]),
                            'username:{}'.format(o_stats.group('username'))] + global_tags
                    connected_time = int(time.time()) - int(o_stats.group('connect_sincet'))
                    self.stats.gauge('openvpn.client.bytesin', o_stats.group('bytesin'), tags=tags)
                    self.stats.gauge('openvpn.client.bytesout', o_stats.group('bytesout'), tags=tags)
                    self.stats.gauge('openvpn.client.conntime', connected_time, tags=tags)

    def tail_log(self, logfile):
        """Fri Sep 29 21:29:59 2017 192.168.1.112:62493 TLS: Username/Password authentication succeeded for username 'jakobant'
Fri Sep 29 21:31:57 2017 192.168.1.112:62787 VERIFY OK: depth=1, C=IS, ST=Rkv, L=Reykjavik, O=Heima, OU=Ops, CN=Heima CA, name=EasyRSA, emailAddress=jakobant@gmail.com
Fri Sep 29 21:31:57 2017 192.168.1.112:62787 VERIFY OK: depth=0, C=IS, ST=Rkv, L=Reykjavik, O=Heima, OU=Ops, CN=globbi, name=EasyRSA, emailAddress=jakobant@gmail.com
AUTH-PAM: BACKGROUND: user 'jakobant' failed to authenticate: Authentication failure"""
        login = re.compile(r".*authentication succeeded.*")
        faild_login = re.compile(r".*failed to authenticate.*")
        for line in Pygtail(logfile):
            match = login.match(line)
            if match:
                print(line)
                self.stats.event('Login success', line, tags=global_tags)
            match = faild_login.match(line)
            if match:
                print(line)
                self.stats.event('Authentication failure', line, tags=global_tags)

if __name__ == "__main__":
    monitor = OpenvpnMonitor(os.getenv('MHOST'), int(os.getenv('MPORT')), 60)
    while 1:
        monitor.connect()
        print(monitor.get_data())
        loadstats = monitor.get_loadstats()
        monitor.parse_loadstats(loadstats)
        status = monitor.get_status()
        monitor.parse_status(status)
        monitor.disconnect()
        monitor.tail_log("/tmp/openvpn.log")
        time.sleep(60)
    #monitor.flush_stats()

    #for data in monitor.get_status().splitlines():
    #    print(data)
