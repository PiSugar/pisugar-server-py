# pisugar-server-py

Python library to communicate with pisugar-server.

## Requirements

python 3.5+

## Usage

Installation

    pip3 install pisugar

Python test code

    from pisugar import test_via_tcp

    test_via_tcp(<YOUR HOST ADDR>)

Python example

    from pisugar import *
    
    conn, event_conn = connect_tcp('raspberrypi.local')
    s = PiSugarServer(conn, event_conn)

    s.register_single_tap_handler(lambda: print('single'))
    s.register_double_tap_handler(lambda: print('double'))

    version = s.get_version()

NOTE: The tap event callback should not block the thread

## License

Apache License Version 2.0
