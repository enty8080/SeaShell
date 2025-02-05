"""
MIT License

Copyright (c) 2020-2024 EntySec

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import socket

from pex.arch import ARCH_AARCH64
from pex.platform import OS_IPHONE, OS_MACOS
from pex.proto.tcp import TCPListener
from pex.proto.http import HTTPListener

from pwny.session import PwnySession, PwnyHTTPSession

from typing import Tuple, Any
from badges import Badges

from seashell.lib.config import Config
from seashell.core.api import *

MODE_TCP = "tcp"
MODE_DTCP = "dtcp"
MODE_HTTP = "http"


class Device(Config, Badges):
    """ Subclass of seashell.core module.

    This subclass of seashell.core module is intended for providing
    an implementation of device controller.
    """

    def __init__(self, session: PwnySession) -> None:
        """ Initialize device.

        :param PwnySession: Pwny session
        :return None: None
        """

        self.device = session

        self.uuid = session.uuid
        self.client = (session.info['Host'], session.info['Port'])
        self.server = ()

        self.name = None
        self.os = None
        self.model = None
        self.serial = None
        self.udid = None

        self.platform = self.device.info['Platform']
        self.arch = self.device.info['Arch']

    def update_details(self) -> None:
        """ Update device details.

        :return None: None
        """

        if self.platform != OS_IPHONE:
            return

        result = self.device.send_command(tag=GATHER_GET_INFO)

        self.name = result.get_string(GATHER_NAME)
        self.os = result.get_string(GATHER_OS)
        self.model = result.get_string(GATHER_MODEL)
        self.serial = result.get_string(GATHER_SERIAL)
        self.udid = result.get_string(GATHER_UDID)

    def locate(self) -> Tuple[str, str]:
        """ Get device current latitude and longitude.

        :return Tuple[str, str]: tuple of latitude and longitude
        """

        if self.platform != OS_IPHONE:
            return

        result = self.device.send_command(tag=LOCATE_GET)

        return result.get_string(LOCATE_LATITUDE), \
            result.get_string(LOCATE_LONGITUDE)

    def kill(self) -> None:
        """ Disconnect the specified device.

        :return None: None
        """

        self.device.close()

    def interact(self) -> None:
        """ Interact with the specified device.

        :return None: None
        """

        if self.platform == OS_IPHONE:
            lookup_path = 'apple_ios'
        elif self.platform == OS_MACOS:
            lookup_path = 'macos'
        else:
            lookup_path = 'generic'

        self.device.console.load_external(
            self.modules_path + lookup_path, session=self.device)
        self.device.console.load_plugins(
            self.plugins_path + lookup_path)

        self.device.interact()


class DeviceHandler(Badges):
    """ Subclass of seashell.core module.

    This subclass of seashell.core module is intended for providing
    an implementation of device handler.
    """

    def __init__(self, host: str, port: int, mode: str = MODE_TCP) -> None:
        """ Start TCP listener on socket pair.

        :param str host: host to listen
        :param int port: port to listen
        :param str mode: listener mode (one of http, tcp, dtcp)
        :return None: None
        :raises RuntimeError: with trailing error message
        """

        self.address = ('', -1)
        self.mode = mode

        if mode in [MODE_TCP, MODE_DTCP]:
            self.handler = TCPListener(host, port, None)
            self.session = PwnySession

        elif mode == MODE_HTTP:
            self.handler = HTTPListener(host, port)
            self.session = PwnyHTTPSession

        else:
            raise RuntimeError("Invalid listener mode specified!")

    def start(self) -> None:
        """ Start TCP listener.

        :return None: None
        """

        self.print_process(f"Listening on port {str(self.handler.port)}...")
        self.handler.listen()

    def stop(self) -> None:
        """ Stop listener.

        :return None: None
        """

        self.handler.stop()

    def wrap(self, client: Any, address: tuple) -> Device:
        """ Wrap client with device object.

        :param Any client: client to wrap
        :param tuple address: client address
        :return Device: device instance
        """

        session = self.session()
        session.info.update({
            'Host': address[0],
            'Port': address[1],
        })
        session.open(client)
        session.identify()

        device = Device(session)
        device.server = self.handler.server
        session.device = device

        return device

    def handle(self) -> Device:
        """ Accept connection and wrap it with Device.

        :return Device: device instance
        """

        if self.mode == MODE_DTCP:
            self.handler.accept()
            egress = self.handler.client

            self.handler.accept()
            ingress = self.handler.client

            client = (egress, ingress)
            address = self.handler.address

        elif self.mode == MODE_HTTP:
            client = self.handler
            address = self.handler.server

        else:
            self.handler.accept()

            client = self.handler.client
            address = self.handler.address

        device = self.wrap(client, address)

        self.print_success(
            f"New device connected - {address[0]}!")

        return device
