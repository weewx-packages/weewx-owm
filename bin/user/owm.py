# Modified 2026-10-22 by weewx-packages: compatibility and tracker repairs.
# Modified 2026-10-23 by weewx-packages: ignore unknown options, honor enable,
#   mask the appid in the debug log.
# Modified 2026-10-23 by weewx-packages: do not start with placeholder appid
#   or station_id.
# Copyright 2013-2020 Matthew Wall
"""
Upload data to OpenWeatherMap
  http://openweathermap.org

Thanks to Antonio Burriel for the dewpoint, longitude, and radiation fixes.

[StdRESTful]
    [[OpenWeatherMap]]
        appid = APPID
        station_id = STATION_ID
"""

# FIXME: set the station lat/lon/alt using [PUT]/stations/{:id}

try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    import Queue as queue
try:
    import cjson as json
    setattr(json, 'dumps', json.encode)
    setattr(json, 'loads', json.decode)
except (ImportError, AttributeError):
    try:
        import simplejson as json
    except ImportError:
        import json
import inspect
import urllib.request

import weewx
import weewx.restx
import weewx.units
from weeutil.weeutil import to_bool

VERSION = "0.10.0"

try:
    # Test for new-style weewx logging by trying to import weeutil.logger
    import weeutil.logger
    import logging
    log = logging.getLogger(__name__)

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logwarn(msg):
        log.warning(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'owm: %s' % msg)

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logwarn(msg):
        logmsg(syslog.LOG_WARNING, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)


def _obfuscate(s):
    return 'X' * (len(s) - 4) + s[-4:]


class OpenWeatherMap(weewx.restx.StdRESTful):
    def __init__(self, engine, config_dict):
        """This service recognizes standard restful options plus the following:

        appid: APPID from OpenWeatherMap

        station_id: station identifier

        latitude: Station latitude in decimal degrees
        Default is station latitude

        longitude: Station longitude in decimal degrees
        Default is station longitude

        altitude: Station altitude in meters
        Default is station altitude
        """
        super(OpenWeatherMap, self).__init__(engine, config_dict)        
        loginf('service version is %s' % VERSION)
        # Check to make sure this version of weewx supports JSON posts.
        # To do this, look for function weewx.restx.RESTThread.get_post_body
        try:
            getattr(weewx.restx.RESTThread, 'get_post_body')
        except AttributeError:
            loginf('WeeWX needs to be upgraded to V3.8 in order to post to OWM')
            loginf('****   OWM upload skipped')
            return

        # get_site_dict() returns None if the section is missing or has
        # enable = false, and removes 'enable' otherwise, as for the
        # uploaders in WeeWX itself.
        site_dict = weewx.restx.get_site_dict(config_dict, 'OpenWeatherMap')
        if site_dict is None:
            return
        # The installer of this extension writes INSERT_APPID_HERE and
        # INSERT_STATION_ID_HERE, and the default weewx.conf uses replace_me
        # for the uploaders in WeeWX itself. A value that is still one of
        # these placeholders has not been configured, so it is treated like
        # a missing option and the uploader does not start.
        placeholders = ('replace_me', 'INSERT_APPID_HERE', 'INSERT_STATION_ID_HERE')
        for option in ('appid', 'station_id'):
            if site_dict.get(option) is None or site_dict[option] in placeholders:
                logerr("Data will not be posted: Missing option '%s'" % option)
                return
        # The options are passed to OpenWeatherMapThread as keyword
        # arguments, so a name it does not accept would raise TypeError and
        # stop WeeWX. Drop such names instead. 'queue' is not an option; the
        # service passes its own queue.
        known = set(inspect.signature(OpenWeatherMapThread.__init__).parameters)
        known -= {'self', 'queue'}
        for key in sorted(set(site_dict) - known):
            logwarn("Ignoring unknown option %s" % key)
            del site_dict[key]
        site_dict.setdefault('latitude', engine.stn_info.latitude_f)
        site_dict.setdefault('longitude', engine.stn_info.longitude_f)
        site_dict.setdefault('altitude', engine.stn_info.altitude_vt[0])
        site_dict['manager_dict'] = weewx.manager.get_manager_dict(
            config_dict['DataBindings'], config_dict['Databases'], 'wx_binding')

        self.archive_queue = queue.Queue()
        self.archive_thread = OpenWeatherMapThread(self.archive_queue, **site_dict)
        self.archive_thread.start()
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        loginf("Data will be uploaded for %s" % site_dict['station_id'])

    def new_archive_record(self, event):
        self.archive_queue.put(event.record)


class OpenWeatherMapThread(weewx.restx.RESTThread):

    # observations we should provide but do not
    # rain_6h mm
    # show_1h mm
    # snow_6h mm
    # snow_24h mm
    # visibility_distance km
    # visibility_prefix (N,E,S,W)
    # clouds[]:distance m
    # clouds[]:condition (SKC,NSC,FEW,SCT,BKN,OVC)
    # clouds[]:cumulus (CB,TCU)
    # weather[]:precipitation
    # weather[]:descriptor
    # weather[]:intensity
    # weather[]:proximity
    # weather[]:obsruration
    # weather[]:other
    #
    # derived quantities we could provide but do not
    # humidex
    # dew_point
    # heat_index
    #
    # observations we could provide but the api does not accept
    # uv
    # luminosity
    # radiation

    _SERVER_URL = 'https://api.openweathermap.org/data/3.0/measurements'
    _DATA_MAP = {
        'dt':          ('dateTime',    1, 0),        # epoch
        'wind_deg':    ('windDir',     1.0, 0.0),    # degrees
        'wind_speed':  ('windSpeed',   0.2777777777, 0.0), # m/s
        'wind_gust':   ('windGust',    0.2777777777, 0.0), # m/s
        'temperature': ('outTemp',     1.0, 0.0),    # C
        'humidity':    ('outHumidity', 1.0, 0.0),    # percent
        'pressure':    ('barometer',   1.0, 0.0),    # mbar?
        'rain_1h':     ('hourRain',    10.0, 0.0),   # mm
        'rain_24h':    ('rain24',      10.0, 0.0),   # mm
        }

    def __init__(self, queue,
                 appid, latitude, longitude, altitude,
                 station_id, manager_dict,
                 server_url=_SERVER_URL, skip_upload=False,
                 post_interval=None, max_backlog=0, stale=None,
                 log_success=True, log_failure=True,
                 timeout=60, max_tries=3, retry_wait=5):
        super(OpenWeatherMapThread, self).__init__(queue,
                                                   protocol_name='OWM',
                                                   manager_dict=manager_dict,
                                                   post_interval=post_interval,
                                                   max_backlog=max_backlog,
                                                   stale=stale,
                                                   log_success=log_success,
                                                   log_failure=log_failure,
                                                   timeout=timeout,
                                                   max_tries=max_tries,
                                                   retry_wait=retry_wait)
        self.appid = appid
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.altitude = float(altitude)
        self.station_id = station_id
        self.server_url = server_url
        self.skip_upload = to_bool(skip_upload)

    def format_url(self, _):
        """Override and return the URL used to post to OWM"""

        url = "%s?appid=%s" % (self.server_url, self.appid)
        return url

    def post_request(self, request, data=None):
        """Override, so that the debug log does not show the appid.

        RESTThread.post_request() logs the full URL when debug is 2 or
        higher, and the URL carries the appid. This version logs it with
        all but the last four characters of the appid masked.
        """
        if data is not None and not isinstance(data, bytes):
            data = data.encode('utf-8')
        if weewx.debug >= 2:
            url = request.get_full_url().replace(self.appid, _obfuscate(self.appid))
            logdbg("%s url: '%s'" % (self.protocol_name, url))
        return urllib.request.urlopen(request, data=data, timeout=self.timeout)

    def get_post_body(self, in_record):
        """Override, then supply the body and MIME type of the POST."""

        # put everything into the right units
        record = weewx.units.to_METRIC(in_record)

        # put data into expected scaling, structure, and format
        values = dict()
        values['station_id'] = self.station_id
        for _key in self._DATA_MAP:
            rkey = self._DATA_MAP[_key][0]
            if rkey in record and record[rkey] is not None:
                values[_key] = record[rkey] * self._DATA_MAP[_key][1] + self._DATA_MAP[_key][2]
        data = json.dumps([values])
        return data, 'application/json'
