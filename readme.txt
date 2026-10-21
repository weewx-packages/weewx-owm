owm - weewx extension that sends data to OpenWeatherMap
Copyright 2014-2020 Matthew Wall
Distributed under the terms of the GNU Public License (GPLv3)

Installation instructions:

1) download

wget -O weewx-owm.zip https://github.com/weewx-packages/weewx-owm/archive/master.zip

2) run the installer:

WeeWX 5:
weectl extension install https://github.com/weewx-packages/weewx-owm/archive/refs/heads/master.zip

WeeWX 4:
wee_extension --install weewx-owm.zip

3) modify weewx.conf:

[StdRESTful]
    [[OpenWeatherMap]]
        appid = OWM_APPID
        station_id = STATION_ID

4) restart weewx

sudo /etc/init.d/weewx stop
sudo /etc/init.d/weewx start

STATION_ID is the internal id returned when you register a station with
POST /data/3.0/stations, or list your stations with GET /data/3.0/stations.
Use the response id, for example 583436dd9643a9000196b8d6. It is distinct
from your appid, city id and external_id.
See https://openweathermap.org/api/stations for station registration.

Modified 2026-10-22 by weewx-packages.
