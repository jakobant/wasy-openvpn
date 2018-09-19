# OpenVPN Monitor data to DataDog

## Summary
Simple python script that uses the management console in Openvpn, queries 
every 60 seconds and sends to DataDog.  Tails OpenVPN log file for Login
and Login Failures and send to DataDog as events.

## DataDog screenshots
### Overview
![Overview](https://github.com/jakobant/wasy-openvpn/raw/master/datadog/DataDogOpenvpnOverview.png)
### Timeboard
§![Timeboard](https://github.com/jakobant/wasy-openvpn/raw/master/datadog/DataDogOpenvpnTimeboard.png)

## Install
Python, add datadog and pygtail

```shell
pip install datadog
pip install pygtail
```

Update add_dashboard.sh and runovpnmonitor.sh, add DataDog api_key and app_key :

```shell
# Edit runovpnmonitor.sh and add keys
export DD_APP_KEY=
export DD_API_KEY=
```

```shell
# edit add_dashboards.sh and add keys
api_key=
app_key=
```

## Configure OpenVPN
Enable management console, add to the openvpn server config.

    ```shell
management 127.0.0.1 5555
```

## Run the monitor for ever:

```shell
./runovpnmonitor.sh

```

## Possible problems.
Yes.
F.e. the magament monitor port only handles one telnet session at at time.
