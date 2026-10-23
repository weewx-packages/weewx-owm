# OpenWeatherMap station uploader for WeeWX

Upload archive observations as JSON to OpenWeatherMap's station measurements
API 3.0. This sends your station data; it does not download forecasts or current
weather from OpenWeatherMap.

This is the weewx-packages continuation of
[matthewwall/weewx-owm](https://github.com/matthewwall/weewx-owm).
[Origin](ORIGIN.md) records the upstream revision; [repair notes](REPAIR_NOTES.md)
describe the maintenance changes.

## Requirements

* An OpenWeatherMap API key with access to the station API.
* A station registered with that API. Follow the
  [station API documentation](https://openweathermap.org/api/stations) to
  register one with `POST /data/3.0/stations`, or list your stations with
  `GET /data/3.0/stations`. The response contains the internal station `id`,
  for example `583436dd9643a9000196b8d6`. It differs from the API key, the city
  ID and `external_id`.

No additional Python package is required.

## Installation

Install `owm` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/owm.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

The installer registers `user.owm.OpenWeatherMap` as a RESTful service and adds
an `[[OpenWeatherMap]]` section with placeholder values. Replace them as shown
below, restart WeeWX, then check its log after the next archive record.

## Configuration

```ini
[StdRESTful]
    [[OpenWeatherMap]]
        appid = YOUR_API_KEY
        station_id = YOUR_INTERNAL_STATION_ID
```

| Option | Default | Meaning |
|---|---|---|
| `appid` | required | OpenWeatherMap API key. |
| `station_id` | required | Internal station `id` from the station API. |
| `server_url` | `https://api.openweathermap.org/data/3.0/measurements` | Measurement endpoint. |
| `skip_upload` | `false` | Build each upload but do not send it. |
| `post_interval` | none | Minimum seconds between uploads. |
| `max_backlog` | `0` | Queued records kept when uploads fall behind. With `0`, only the newest record is sent. |
| `stale` | none | Skip records older than this many seconds. |
| `log_success` | `true` | Log each successful upload. |
| `log_failure` | `true` | Log each failed upload. |
| `timeout` | `60` | Seconds to wait for the server. |
| `max_tries` | `3` | Attempts per record. |
| `retry_wait` | `5` | Seconds between attempts. |

Each upload contains the time, wind direction, speed and gust, temperature,
humidity, barometer, hourly rain and 24-hour rain, as far as the record has
them. Values are converted to Celsius, m/s, mbar and mm. When a record has no
hourly or 24-hour rain, WeeWX sums it from the archive of `wx_binding`.

## Limitations

* Every option in `[[OpenWeatherMap]]` is passed to the uploader. Any option
  not named on this page, including `enable`, stops WeeWX at startup. To turn
  the uploader off, remove `user.owm.OpenWeatherMap` from `restful_services`
  in `[Engine]`.
* The uploader does not register stations or update their location metadata.
  `latitude`, `longitude` and `altitude` are accepted but not sent. Set that
  metadata with the station API.
* Observations without an entry in `_DATA_MAP` in
  [bin/user/owm.py](bin/user/owm.py) are not sent. This includes UV and solar
  radiation.
* The tests use local receivers. They do not check your OpenWeatherMap
  account, its permissions, or whether OpenWeatherMap accepts your station's
  data.

## Development

```sh
python -m pytest -q tests
```

Run it in a Python environment with WeeWX and pytest installed.

## License

Copyright 2014-2020 Matthew Wall. [GNU GPLv3](license).

Thanks to Antonio Burriel for the dewpoint, longitude and radiation fixes in
the earlier implementation.
