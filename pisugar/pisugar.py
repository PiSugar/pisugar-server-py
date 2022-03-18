# -*- coding=utf-8 -*-

import socket
import sys
import threading
from time import sleep
from datetime import datetime


def connect_domain_socket(file="/tmp/pisugar-server.sock"):
    """Connect pisugar server via unix domain socket file"""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn = s.connect(file)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    event_conn = s.connect(file)
    return (conn, event_conn)


def connect_tcp(host="127.0.0.1", port=8423, timeout: float = None) -> tuple[socket.socket, socket.socket]:
    """Connect pisugar server via tcp"""
    conn = socket.create_connection((host, port), timeout)
    event_conn = socket.create_connection((host, port), timeout)
    return (conn, event_conn)


# def connect_ws(host="127.0.0.1", port=8421, path="/ws", username=None, password=None):
#     """Connect pisugar server via websocket"""
#     pass


def _get_parse_str(resp: bytes) -> str:
    pos = resp.find(b':')
    return str(resp[pos+1:], encoding='utf-8').strip(" \n")


def _get_parse_float(resp: bytes) -> float:
    return float(_get_parse_str(resp))


def _get_parse_int(resp: bytes) -> int:
    return int(_get_parse_str(resp))


def _get_parse_bool(resp: bytes) -> bool:
    return _get_parse_str(resp).lower().find('true') >= 0


def _set_assert_done(resp: bytes):
    if not resp.find(b'done') >= 0:
        raise Exception(str(resp, encoding='utf-8'))


class PiSugarServer:
    """PiSugar Server API"""

    def __init__(self, conn: socket.socket, event_conn: None):
        """Init api connection
        
        conn: normal connection
        event_conn: event connection, could be None
        """
        self._conn = conn
        if event_conn:
            self._single_tap_handlers = []
            self._double_tap_handlers = []
            self._long_tap_handlers = []
            self._event_conn = event_conn
            self._event_thread = threading.Thread(
                target=self._start_poll_event)
            self._event_thread.setDaemon(True)
            self._event_thread.start()

    def register_single_tap_handler(self, callback):
        """Register single tap event handler"""
        if not self._event_conn:
            raise Exception("Event connection is not specified")
        self._single_tap_handlers.append(callback)

    def register_double_tap_handler(self, callback):
        """Register double tap event handler"""
        if not self._event_conn:
            raise Exception("Event connection is not specified")
        self._double_tap_handlers.append(callback)

    def register_long_tap_handler(self, callback):
        """Register long tap event handler"""
        if not self._event_conn:
            raise Exception("Event connection is not specified")
        self._long_tap_handlers.append(callback)

    def _start_poll_event(self):
        while True:
            try:
                event = self._event_conn.recv(4096)
                if event == b'single':
                    for handler in self._single_tap_handlers:
                        handler()
                elif event == b'double':
                    for handler in self._double_tap_handlers:
                        handler()
                elif event == b'long':
                    for handler in self._long_tap_handlers:
                        handler()
                else:
                    print("Invalid event:", str(event), file=sys.stderr)
            except Exception as ex:
                print("Exception: ", ex, file=sys.stderr)
                sleep(1)

    def _send_and_recv_parse(self, cmd: bytes, expected: bytes, parser=None):
        self._conn.sendall(cmd)
        for i in range(3):
            resp = self._conn.recv(4096)
            resp = resp.replace(b'single', b'')
            resp = resp.replace(b'double', b'')
            resp = resp.replace(b'long', b'')
            if not resp:
                continue
            if not resp.find(expected) >= 0:
                raise Exception(
                    'Expected {} but got {}'.format(expected, resp))
            if parser is not None:
                return parser(resp)
            return resp
        raise Exception("Too many retries")

    def _get_and_parse(self, expected: bytes, parser):
        return self._send_and_recv_parse(b'get ' + expected, expected, parser)

    def _set_and_assert(self, expected: bytes, *args):
        cmd = expected + b' ' + b' '.join(args)
        return self._send_and_recv_parse(cmd, expected, _set_assert_done)

    def get_version(self) -> str:
        """Get server version"""
        return self._get_and_parse(b'version', _get_parse_str)

    def get_model(self) -> str:
        """Get model"""
        return self._get_and_parse(b'model', _get_parse_str)

    def get_fireware_version(self) -> str:
        """Get fireware version (pisugar 3)"""
        return self._get_and_parse(b'fireware_version', _get_parse_str)

    def get_battery_level(self) -> float:
        """Get battery level(%)"""
        return self._get_and_parse(b'battery', _get_parse_float)

    def get_battery_voltage(self) -> float:
        """Get battery valtage(V)"""
        return self._get_and_parse(b'battery_v', _get_parse_float)

    def get_battery_current(self) -> float:
        """Get battery current(A)"""
        return self._get_and_parse(b'battery_i', _get_parse_float)

    def get_battery_led_amount(self):
        """Get battery led amount (pisugar 2)"""
        return self._get_and_parse(b'battery_led_amount', _get_parse_int)

    def get_battery_power_plugged(self):
        """Is battery power plugged"""
        return self._get_and_parse(b'battery_power_plugged', _get_parse_bool)

    def get_battery_allow_charging(self):
        """Is battery allow charging"""
        return self._get_and_parse(b'battery_allow_charging', _get_parse_bool)

    def get_battery_charging_range(self):
        """Battery charing range"""
        s = self._get_and_parse(b'battery_charging_range', _get_parse_str)
        if s.find(',') > 0:
            return (float(s.split(',')[0]), float(s.split(',')[1]))
        return None

    def get_battery_charging(self):
        """Is battery charging"""
        return self._get_and_parse(b'battery_charging', _get_parse_bool)

    def get_battery_input_protect_enabled(self):
        """Is battery input protect enabled"""
        return self._get_and_parse(b'battery_input_protect_enabled', _get_parse_bool)

    def get_battery_output_enabled(self):
        """Is battery output enabled"""
        return self._get_and_parse(b'battery_output_enabled', _get_parse_bool)

    def get_battery_full_charge_duration(self):
        """Duration of keeping charging the battery after it is full"""
        s = self._get_and_parse(b'full_charge_duration', _get_parse_str)
        try:
            return int(s)
        except Exception as ex:
            return None

    def get_battery_safe_shutdown_level(self):
        """Get battery safe shutdown level"""
        return self._get_and_parse(b'safe_shutdown_level', _get_parse_float)

    def get_battery_safe_shutdown_delay(self):
        """Get battery safe shutdown delay (seconds before disable output)"""
        return self._get_and_parse(b'safe_shutdown_delay', _get_parse_int)

    def get_battery_auto_power_on(self):
        """Get battery auto power on (after power restore)

        Note:
            pisugar2 -> the rtc will wake up the power management unit every few seconds
            pisugar3 -> works fine
        """
        return self._get_and_parse(b'auto_power_on', _get_parse_bool)

    def get_battery_input_protect(self):
        """Is battery input protect enabled"""
        return self._get_and_parse(b'input_protect', _get_parse_bool)

    def get_battery_soft_poweroff(self):
        """Is battery soft poweroff enabled (pisugar 3)"""
        return self._get_and_parse(b'soft_poweroff', _get_parse_bool)

    def get_system_time(self):
        """Get os datetime"""
        s = self._get_and_parse(b'system_time', _get_parse_str)
        return datetime.fromisoformat(s)

    def get_rtc_time(self):
        """Get rtc datetime"""
        s = self._get_and_parse(b'rtc_time', _get_parse_str)
        return datetime.fromisoformat(s)

    def get_rtc_alarm_time(self):
        """Get rtc alarm time (The date part has no meaning)"""
        s = self._get_and_parse(b'rtc_alarm_time', _get_parse_str)
        try:
            return datetime.fromisoformat(s)
        except Exception as ex:
            return None

    def get_rtc_alarm_enabled(self):
        """Is rtc alarm enabled"""
        return self._get_and_parse(b'rtc_alarm_enabled', _get_parse_bool)

    def get_rtc_adjust_ppm(self):
        """Get rtc adjust ppm (pisugar 3)"""
        return self._get_and_parse(b'rtc_adjust_ppm', _get_parse_int)

    def get_rtc_alarm_repeat(self):
        """Get rtc alam repeat (bit 0-6 means Sunday to Saturday)"""
        return self._get_and_parse(b'alarm_repeat', _get_parse_int)

    def get_tap_enable(self, tap='single'):
        """Is tap function enabled

        tap: 'single' or 'double' or 'long'
        """
        resp = self._send_and_recv_parse(
            b'get button_enable ' + tap.encode('utf-8'), b'button_enable')
        return resp.lower().find(b'true') >= 0

    def get_tap_shell(self, tap='single'):
        """Get tap shell script

        tap: 'single' or 'double' or 'long'
        """
        resp = self._send_and_recv_parse(
            b'get button_shell ' + tap.encode('utf-8'), b'button_shell', _get_parse_str)
        pos = resp.find(tap)
        return resp[pos:]

    def get_auth_username(self):
        """Get http auth username"""
        return self._get_and_parse(b'auth_username', _get_parse_str)

    def get_anti_mistouch(self):
        """Is power button anti-mistouch enabled (pisugar 3)"""
        return self._get_and_parse(b'anti_mistouch', _get_parse_bool)

    def get_temperature(self):
        """Get pisugar templature"""
        return self._get_and_parse(b'temperature', _get_parse_float)

    def set_battery_charging_range(self, lower_bound: float, upper_bound: float):
        """Set battery charging range

        0.0 <= lower_bound < upper_bound <= 100.0
        """
        arg = ','.join([str(lower_bound), str(upper_bound)]).encode("utf-8")
        return self._set_and_assert(b'set_battery_charging_range', arg)

    def set_battery_input_protect(self, enable: bool):
        """Enable/disable battery input protece"""
        arg = b'true' if enable else b'false'
        return self._set_and_assert(b'set_battery_input_protect', arg)

    def set_battery_output(self, enable: bool):
        """Enable/disable battery output"""
        arg = b'true' if enable else b'false'
        return self._set_and_assert(b'set_battery_output', arg)

    def set_battery_full_charge_duration(self, seconds: int):
        """Set duration of seconds after battery is full"""
        arg = str(seconds).encode("utf-8")
        return self._set_and_assert(b'set_full_charge_duration', arg)

    def set_battery_allow_charging(self, enable: bool):
        """Enable/disable charging"""
        arg = b'true' if enable else b'false'
        return self._set_and_assert(b'set_allow_charging', arg)

    def set_battery_safe_shutdown_level(self, level: float):
        """Set battery safe shutdown level

        level: should between 0.0 and 60.0
        """
        return self._set_and_assert(b'set_safe_shutdown_level', str(level).encode("utf-8"))

    def set_battery_safe_shutdown_delay(self, delay: int):
        """Delay seconds before safe shutdown"""
        return self._set_and_assert(b'set_safe_shutdown_delay', str(delay).encode("utf-8"))

    def set_battery_auto_power_on(self, enable: bool):
        """Enable/disable auto power on"""
        arg = b'true' if enable else b'false'
        return self._set_and_assert(b'set_auto_power_on', arg)

    def set_battery_force_shutdown(self):
        """Disable battery output and shutdown pisugar"""
        return self._set_and_assert(b'force_shutdown')

    def set_battery_soft_poweroff(self, enable: bool):
        """Enable/disable soft poweroff"""
        arg = b'true' if enable else b'false'
        return self._set_and_assert(b'set_soft_poweroff', arg)

    def set_battery_input_protect(self, enable: bool):
        arg = b'true' if enable else b'false'
        return self._set_and_assert(b'set_input_protect', arg)

    def rtc_pi2rtc(self):
        """Replace rtc time with os time"""
        return self._set_and_assert(b'rtc_pi2rtc')

    def rtc_rtc2pi(self):
        """Replace os time with rtc time"""
        return self._set_and_assert(b'rtc_rtc2pi')

    def rtc_web(self):
        """Repace rtc/os time with network time"""
        return self._set_and_assert(b'rtc_web')

    def rtc_alarm_set(self, time: datetime, weekday_repeat: 127):
        """Set rtc alarm time

        time: date part (yyyy/MM/dd) is ignored
        weekday_repeat: bit0-6 is Sunday to Saturday
        """
        if time.tzinfo is None:
            time = time.astimezone()
        args = [time.isoformat().encode(
            'utf-8'), str(weekday_repeat).encode('utf-8')]
        return self._set_and_assert(b'rtc_alarm_set', *args)

    def rtc_alarm_disable(self):
        """Disable alarm"""
        return self._set_and_assert(b'rtc_alarm_disable')

    def rtc_adjust_ppm(self, ppm: float):
        """Adjust rtc ppm

        ppm: should between -500.0 and 500.0
        """
        return self._set_and_assert(b'rtc_adjust_ppm', str(ppm).encode('utf-8'))

    def set_tap_enable(self, tap: str, enable: bool):
        """Enable/disable tap

        tap: 'single' or 'double' or 'long'
        """
        args = [tap.encode('utf-8'), b'1' if enable else b'0']
        return self._set_and_assert(b'set_button_enable', *args)

    def set_button_shell(self, tap: str, shell: str):
        """Set tap event shell script"""
        args = [tap.encode("utf-8"), shell.encode("utf-8")]
        return self._set_and_assert(b'set_button_shell', *args)

    def set_auth(self, username: str, password: str):
        """Set http auth username and password"""
        return self._set_and_assert(b'set_auth', username.encode("utf-8"), password.encode("utf-8"))

    def set_anti_mistouch(self, enable: bool):
        """Enable/disable anti-mistouch"""
        arg = b'true' if enable else b'false'
        return self._set_and_assert(b'set_anti_mistouch', arg)


def _print_wait(*args):
    print(*args)
    sleep(0.2)

def test_via_tcp(host="localhost", port=8423, test_set=False):
    """Test pisugar api
    
    host: pisugar host
    port: pisugar tcp port
    test_set: test set_* functions
    """
    conn, event_conn = connect_tcp(host, port)
    pisugar = PiSugarServer(conn, event_conn)

    pisugar.register_single_tap_handler(lambda: print('single'))
    pisugar.register_double_tap_handler(lambda: print('double'))
    pisugar.register_long_tap_handler(lambda: print('long'))

    print('get_version', pisugar.get_version())
    print('get_model', pisugar.get_model())
    print('get_battery_level', pisugar.get_battery_level())
    print('get_battery_voltage', pisugar.get_battery_voltage())
    print('get_battery_current', pisugar.get_battery_current())
    print('get_battery_led_amount', pisugar.get_battery_led_amount())
    print('get_battery_power_plugged', pisugar.get_battery_power_plugged())
    print('get_battery_allow_charging', pisugar.get_battery_allow_charging())
    print('get_battery_charging_range', pisugar.get_battery_charging_range())
    print('get_battery_charging', pisugar.get_battery_charging())
    print('get_battery_input_protect_enabled',
          pisugar.get_battery_input_protect_enabled())
    print('get_battery_output_enabled', pisugar.get_battery_output_enabled())
    print('get_battery_full_charge_duration',
          pisugar.get_battery_full_charge_duration())
    print('get_battery_safe_shutdown_level',
          pisugar.get_battery_safe_shutdown_level())
    print('get_battery_safe_shutdown_delay',
          pisugar.get_battery_safe_shutdown_delay())
    print('get_battery_auto_power_on', pisugar.get_battery_auto_power_on())
    print('get_battery_soft_poweroff', pisugar.get_battery_soft_poweroff())
    print('get_battery_input_protect', pisugar.get_battery_input_protect())

    print('get_system_time', pisugar.get_system_time())
    print('get_rtc_time', pisugar.get_rtc_time())
    print('get_rtc_alarm_time', pisugar.get_rtc_alarm_time())
    print('get_rtc_alarm_enabled', pisugar.get_rtc_alarm_enabled())
    print('get_rtc_adjust_ppm', pisugar.get_rtc_adjust_ppm())
    print('get_rtc_alarm_repeat', pisugar.get_rtc_alarm_repeat())

    print('get_tap_enable single', pisugar.get_tap_enable('single'))
    print('get_tap_enable double', pisugar.get_tap_enable('double'))
    print('get_tap_enable long', pisugar.get_tap_enable('long'))
    print('get_tap_shell single', pisugar.get_tap_shell('single'))
    print('get_tap_shell double', pisugar.get_tap_shell('double'))
    print('get_tap_shell long', pisugar.get_tap_shell('long'))

    print('get_temperature', pisugar.get_temperature())

    if test_set:
        _print_wait('set_battery_charging_range 60 80',
              pisugar.set_battery_charging_range(60, 80))
        _print_wait('set_battery_input_protect False',
              pisugar.set_battery_input_protect(False))
        _print_wait('set_battery_output True', pisugar.set_battery_output(True))
        _print_wait('set_battery_full_charge_duration 120',
              pisugar.set_battery_full_charge_duration(120))
        _print_wait('set_battery_allow_charging True',
              pisugar.set_battery_allow_charging(True))
        _print_wait('set_battery_safe_shutdown_level 20',
              pisugar.set_battery_safe_shutdown_level(20))
        _print_wait('set_battery_safe_shutdown_delay 3',
              pisugar.set_battery_safe_shutdown_delay(3))
        _print_wait('set_battery_auto_power_on False',
              pisugar.set_battery_auto_power_on(False))
        _print_wait('set_battery_soft_poweroff False',
              pisugar.set_battery_soft_poweroff(False))
        _print_wait('set_battery_input_protect False',
              pisugar.set_battery_input_protect(False))

        _print_wait('rtc_pi2rtc', pisugar.rtc_pi2rtc())
        _print_wait('rtc_rtc2pi', pisugar.rtc_rtc2pi())
        _print_wait('rtc_web', pisugar.rtc_web())
        _print_wait('rtc_alarm_set', pisugar.rtc_alarm_set(
            datetime(2000, 1, 1, 12, 0, 0), 127))
        _print_wait('rtc_alarm_disable', pisugar.rtc_alarm_disable())
        _print_wait('rtc_adjust_ppm', pisugar.rtc_adjust_ppm(0))

        _print_wait("set_tap_enable", pisugar.set_tap_enable('single', False))
        _print_wait("set_tap_shell", pisugar.set_button_shell('single', ''))

        _print_wait("set_anti_mistouch True", pisugar.set_anti_mistouch(True))
