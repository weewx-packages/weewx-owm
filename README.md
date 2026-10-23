# OpenWeatherMap station uploader for WeeWX

Upload archive observations as JSON to OpenWeatherMap's station measurements
API 3.0. This sends your station data; it does not download forecasts or current
weather from OpenWeatherMap.

This is the weewx-packages continuation, release **0.10.0**.
[Origin](ORIGIN.md) records the upstream revision; [repair notes](REPAIR_NOTES.md)
describe the maintenance changes.

The catalog archive targets WeeWX `>=5.5.2,<5.7` and Python `>=3.10,<3.15`.

## Install

Use `weectl` from the Python environment running WeeWX. With stock WeeWX 5,
install the published archive:

```sh
weectl extension install https://github.com/weewx-packages/weewx-owm/releases/download/v0.10.0/weewx-owm-0.10.0.tar.gz --config /path/to/weewx.conf
```

Replace `/path/to/weewx.conf` with your station configuration. You can also
download that URL and pass the local archive to the same command. Use elevated
permissions only when your station files require them.

## Register and configure a station

You need an OpenWeatherMap API key with access to the station API and an already
registered station. No additional Python package is required. Follow the
[station API documentation](https://openweathermap.org/api/stations) to register
with `POST /data/3.0/stations`, or list your stations with `GET /data/3.0/stations`.
Use the returned internal `id` as `station_id`, for example
`583436dd9643a9000196b8d6`. It differs from the API key, city ID and `external_id`.

```ini
[StdRESTful]
    [[OpenWeatherMap]]
        appid = YOUR_API_KEY
        station_id = YOUR_INTERNAL_STATION_ID
```

The installer registers `user.owm.OpenWeatherMap`. Restart WeeWX yourself, then
check its log after the next archive record. The destination is
`https://api.openweathermap.org/data/3.0/measurements`.

## Measurements and limits

The upload includes time, wind direction, speed and gust, temperature,
humidity, barometric pressure, hourly rain and 24-hour rain when available.
It converts values to Celsius, m/s, mbar and mm before creating the JSON array.
Archive augmentation uses `wx_binding` for rain totals.

The uploader does not register stations or update their location metadata.
Configure that metadata with the station API. Fields without an entry in
[`_DATA_MAP`](bin/user/owm.py), including UV and solar radiation, are not sent.
API access, account permissions and acceptance of your station's data require
checking your own OpenWeatherMap account.

Copyright 2014-2020 Matthew Wall. [GNU GPLv3](license).
Thanks to Antonio Burriel for the dewpoint, longitude and radiation fixes in
the earlier implementation.
