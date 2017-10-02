# OpenVPN Monitor data to DataDog

## Summary
Simple python script that uses the management console in Openvpn, queries 
every 60 seconds and sends to DataDog.  Tails OpenVPN log file for Login
and Login Failures and send to DataDog as events.

## DataDog screenshots
### Overview
![Overview](https://github.com/jakobant/wasy-openvpn/raw/master/datadog/DataDogOpenvpnOverview.png)
### Timeboard
![Timeboard](https://github.com/jakobant/wasy-openvpn/raw/master/datadog/DataDogOpenvpnTimeboard.png)

## Install


### Configure OpenVPN
Enable management console, add to the openvpn server config.
```shell
management 127.0.0.1 5555```