#!/bin/bash

export DD_APP_KEY=
export DD_API_KEY=
export MHOST=127.0.0.1
export MPORT=5555

while true
do
python telnet-monitor.py
sleep 60
done
