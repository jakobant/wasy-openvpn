#!/bin/bash

api_key=
app_key=

#Add Dashboards, set you api_key and app_key
curl -X POST -H "Content-type: application/json" "https://app.datadoghq.com/api/v1/dash?api_key=${api_key}&application_key=${app_key}" -d@timeboard.json
curl -X POST -H "Content-type: application/json" "https://app.datadoghq.com/api/v1/screen?api_key=${api_key}&application_key=${app_key}" -d@overview.json
