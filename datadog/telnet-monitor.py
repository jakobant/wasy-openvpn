#!/usr/bin/env python
import socket
import select
import sys
import os
import re
import logging
import time
from datadog import initialize, ThreadStats
from pygtail import Pygtail

class OpenvpnMonitor:
    def __init__(self, monitor_host, monitor_port, interval):
        self.host = monitor_host
        self.port = monitor_port
        self.interval = interval
        self.s = None
        self.stats = ThreadStats()
        self.init_datadog()
        self.stats.start(flush_interval=interval, flush_in_thread=False)
        self.base_tags = ['server:{}'.format(os.uname()[1]), 'type:openvpn']
        self.tags = self.base_tags.copy()

    def init_datadog(self):
        options = {
            'api_key': os.getenv('DD_API_KEY'),
            'app_key': os.getenv('DD_APP_KEY')
        }
        initialize(**options)
        logging.basicConfig(level=logging.DEBUG)

    def connect(self):
        try:
            self.s = socket.create_connection((self.host, self.port), 2)
        except Exception as e:
            logging.error(f'Unable to connect: {e}')
            sys.exit(1)

    def disconnect(self):
        if self.s:
            try:
                self.s.send('quit\n'.encode('ascii'))
                self.s.shutdown(socket.SHUT_RDWR)
                self.s.close()
            except Exception as e:
                logging.error(f'Error disconnecting: {e}')

    def send_command(self, command):
        self.s.send(f"{command}\n".encode('ascii'))
        response = ""
        while True:
            ready_to_read, _, _ = select.select([self.s], [], [], 2)
            if ready_to_read:
                data = self.s.recv(4096)
                if not data:
                    break
                response += data.decode('utf-8')
            else:
                break
        return response

    def get_version(self):
        return self.send_command('version')

    def get_loadstats(self):
        return self.send_command('load-stats')

    def get_status(self):
        return self.send_command('status 2')

    def parse_version(self, version):
        ver = version.split()
        if len(ver) > 3:
            version_tag = f"version:{ver[2]}_{ver[3]}"
            self.tags = self.base_tags + [version_tag]
            logging.debug(f'Parsed version: {version_tag}')

    def parse_loadstats(self, loadstats):
        pattern = re.compile(r"SUCCESS:.*nclients=(\d*),bytesin=(\d*),bytesout=(\d*).*")
        match = pattern.search(loadstats)
        if match:
            nclients = int(match.group(1))
            bytesin = int(match.group(2))
            bytesout = int(match.group(3))
            logging.debug(f'Parsed loadstats: nclients={nclients}, bytesin={bytesin}, bytesout={bytesout}')
            self.stats.gauge('openvpn.nclients', nclients, tags=self.tags)
            self.stats.gauge('openvpn.bytesin', bytesin, tags=self.tags)
            self.stats.gauge('openvpn.bytesout', bytesout, tags=self.tags)

    def parse_status(self, status):
        COMMONNAME = 1
        REAL_ADDR = 2
        VIRT_ADDR = 3
        BYTESIN = 5
        BYTESOUT = 6
        USERNAME = 9
        CONN_SINCET = 8
        for line in status.splitlines():
            if line.startswith('CLIENT_LIST'):
                parts = line.split(',')
                if len(parts) < 10:
                    BYTESIN = 4
                    BYTESOUT = 5
                    USERNAME = 8
                    CONN_SINCET = 7
                tags = [
                    f'commonname:{parts[COMMONNAME]}',
                    f'real_addr:{parts[REAL_ADDR].split(":")[0]}',
                    f'virt_addr:{parts[VIRT_ADDR]}',
                    f'username:{parts[USERNAME]}'
                ] + self.tags
                connected_time = int(time.time()) - int(parts[CONN_SINCET])
                logging.debug(f'Parsed status: commonname={parts[COMMONNAME]}, real_addr={parts[REAL_ADDR].split(":")[0]}, virt_addr={parts[VIRT_ADDR]}, username={parts[USERNAME]}, connected_time={connected_time}')
                self.stats.gauge('openvpn.client.bytesin', int(parts[BYTESIN]), tags=tags)
                self.stats.gauge('openvpn.client.bytesout', int(parts[BYTESOUT]), tags=tags)
                self.stats.gauge('openvpn.client.conntime', connected_time, tags=tags)

    def tail_log(self, logfile):
        login = re.compile(r".*authentication succeeded.*")
        failed_login = re.compile(r".*(failed to authenticate|Incorrect password|was not found).*")
        for line in Pygtail(logfile):
            if login.match(line):
                logging.debug(f'Login success: {line.strip()}')
                self.stats.event('Login success', line.strip(), alert_type='success', tags=self.tags)
            if failed_login.match(line):
                logging.debug(f'Authentication failure: {line.strip()}')
                self.stats.event('Authentication failure', line.strip(), alert_type='error', tags=self.tags)

    def run(self):
        while True:
            self.connect()
            version = self.get_version()
            self.parse_version(version)
            loadstats = self.get_loadstats()
            self.parse_loadstats(loadstats)
            status = self.get_status()
            self.parse_status(status)
            self.disconnect()
            self.tail_log(os.getenv('OVPN_LOGS', '/var/log/openvpn/openvpn.log'))
            self.flush_datadog()
            self.reset_tags()  # Reset tags to base tags periodically
            time.sleep(self.interval)

    def flush_datadog(self):
        self.stats.flush()

    def reset_tags(self):
        self.tags = self.base_tags.copy()
        logging.debug('Tags reset to base tags.')

if __name__ == "__main__":
    monitor = OpenvpnMonitor(os.getenv('MHOST'), int(os.getenv('MPORT')), 60)
    monitor.run()
