#!env python
import socket
import select
import sys
import os
import re
import logging
import time
from datadog import initialize
options = {
    'api_key': 'c06481d50c5f3afa3a62c82deb8a14ad',
    'app_key': 'fa8a8be4f47b3ef05174520aad84d9de2b23ea5d'
}
initialize(**options)
logging.basicConfig(level=logging.DEBUG)


# main function

class OpenvpnMonitor():

    def __init__(self, monitor_host, monitor_port, interval, datadog=True, elstic=False):
        self.host = monitor_host
        self.port = monitor_port
        self.interval = interval
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(2)
        self.datadog = datadog
        try:
            self.s.connect((self.host, self.port))
        except:
            print('Unable to connect')
            sys.exit()
        from datadog import ThreadStats
        self.stats = ThreadStats()
        self.stats.start(flush_interval=interval)

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
                            'username:{}'.format(o_stats.group('username'))]
                    self.stats.gauge('openvpn.client.bytesin', o_stats.group('bytesin'), tags=tags)
                    self.stats.gauge('openvpn.client.bytesout', o_stats.group('bytesout'), tags=tags)
                    self.stats.gauge('openvpn.client.conntime', o_stats.group('connect_sincet'), tags=tags)


if __name__ == "__main__":
    monitor = OpenvpnMonitor('192.168.99.100', 32085, 60)
    print(monitor.get_data())
    while 1:
        loadstats = monitor.get_loadstats()
        monitor.parse_loadstats(loadstats)
        status = monitor.get_status()
        monitor.parse_status(status)
        time.sleep(60)
    #monitor.flush_stats()

    #for data in monitor.get_status().splitlines():
    #    print(data)
