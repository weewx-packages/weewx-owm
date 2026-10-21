# Repair validation

Version 0.10.0. Original repository and revision are in ORIGIN.md.

* https://github.com/matthewwall/weewx-owm/pull/4: Documented WeeWX 5 weectl installation alongside WeeWX 4. Isolated install passes on both. Default measurement endpoint switched to verified HTTPS.
* https://github.com/matthewwall/weewx-owm/issues/3: station_id is the station registration response internal id, distinct from external_id/appid/city id. Opaque id preserved in actual local JSON HTTP post.

Tests run under WeeWX 4.10.2/5.1.0 on Python 3.10 and WeeWX 5.5.2 on Python 3.14. Local receivers and isolated install directories avoid live station changes. The tests do not establish individual external account permissions.
