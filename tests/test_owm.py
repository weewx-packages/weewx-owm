import http.server
import json
import queue
import threading

import pytest
import weewx
import owm


def test_station_id_and_measurements_reach_local_receiver():
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, self.headers['Content-Type'], json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1',0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        worker = owm.OpenWeatherMapThread(queue.Queue(), 'local-key', 50, 8, 100, '583436dd9643a9000196b8d6', None, server_url='http://127.0.0.1:%d/measurements'%server.server_port)
        worker.process_record({'dateTime':1700000000,'usUnits':weewx.US,'outTemp':32,'windSpeed':0,'outHumidity':None},None)
        path, content, records = received[0]
        assert path == '/measurements?appid=local-key'
        assert content == 'application/json'
        assert records[0]['station_id'] == '583436dd9643a9000196b8d6'
        assert records[0]['temperature'] == pytest.approx(0)
        assert records[0]['wind_speed'] == 0
        assert 'humidity' not in records[0]
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_default_endpoint_uses_tls():
    assert owm.OpenWeatherMapThread._SERVER_URL.startswith('https://')


def _service(tmp_path, monkeypatch, **options):
    import types
    import configobj
    monkeypatch.setattr(owm.OpenWeatherMapThread, 'start', lambda self: None)
    engine = types.SimpleNamespace(
        stn_info=types.SimpleNamespace(latitude_f=50.0, longitude_f=8.0, altitude_vt=(100, 'meter', 'group_altitude')),
        bind=lambda *args: None)
    site = {'appid': 'local-key', 'station_id': 'station'}
    site.update(options)
    config = configobj.ConfigObj({
        'WEEWX_ROOT': str(tmp_path),
        'StdRESTful': {'OpenWeatherMap': site},
        'DataBindings': {'wx_binding': {'database': 'archive', 'manager': 'weewx.manager.Manager', 'table_name': 'archive'}},
        'Databases': {'archive': {'database_type': 'SQLite', 'database_name': 'weewx.sdb'}},
        'DatabaseTypes': {'SQLite': {'driver': 'weedb.sqlite', 'SQLITE_ROOT': str(tmp_path)}}})
    return owm.OpenWeatherMap(engine, config)


def test_unknown_option_is_ignored_with_warning(tmp_path, monkeypatch, caplog):
    service = _service(tmp_path, monkeypatch, post_everything='yes', timeout='5')
    assert service.archive_thread.timeout == 5
    assert 'Ignoring unknown option post_everything' in caplog.text


def test_enable_false_skips_the_uploader(tmp_path, monkeypatch):
    assert not hasattr(_service(tmp_path, monkeypatch, enable='false'), 'archive_thread')
    assert hasattr(_service(tmp_path, monkeypatch, enable='true'), 'archive_thread')


def test_debug_log_masks_appid(monkeypatch, caplog):
    import logging

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    monkeypatch.setattr(weewx, 'debug', 2)
    caplog.set_level(logging.DEBUG)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        worker = owm.OpenWeatherMapThread(queue.Queue(), 'SECRETKEY1234', 50, 8, 100, 'station', None, server_url='http://127.0.0.1:%d/measurements' % server.server_port)
        worker.process_record({'dateTime': 1700000000, 'usUnits': weewx.US, 'outTemp': 32}, None)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    assert 'appid=XXXXXXXXX1234' in caplog.text
    assert 'SECRETKEY1234' not in caplog.text


@pytest.mark.parametrize('option,value', [('appid', 'INSERT_APPID_HERE'), ('station_id', 'INSERT_STATION_ID_HERE'), ('appid', 'replace_me')])
def test_placeholder_keeps_the_uploader_off(tmp_path, monkeypatch, caplog, option, value):
    assert not hasattr(_service(tmp_path, monkeypatch, **{option: value}), 'archive_thread')
    assert "Data will not be posted: Missing option '%s'" % option in caplog.text
