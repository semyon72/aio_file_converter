# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: soffice_options.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-16 (y-m-d) 4:19 PM

import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request

import cmd_options as cmdopt

from sysproc_tools import get_local_ips

get_local_ips_cached = functools.cache(get_local_ips)


@dataclass
class ProgramSOCmdOption(cmdopt.KeylessCmdOption):
    order: int = -1
    name: str = 'program'
    cmd_value: str = 'soffice'


@dataclass
class UserProfileDirSOCmdOption(cmdopt.KeylessCmdOption):
    order: int = 10
    name: str = 'user_profile_dir'
    cmd_value: str = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == 'cmd_value' and value:
            value = str(value)
            if not Path(value).is_dir():
                raise ValueError(f'directory {value} does not exist')
            value = f'-env:UserInstallation=file://{request.pathname2url(value)}'
        super().__setattr__(name, value)


@dataclass
class HeadlessSOCmdOption(cmdopt.ValuelessCmdOption):
    order: int = 20
    name: str = 'headless'
    cmd_key: str = '--headless'


@dataclass
class InvisibleSOCmdOption(cmdopt.ValuelessCmdOption):
    order: int = 20
    name: str = 'invisible'
    cmd_key: str = '--invisible'


@dataclass
class NocrashreportSOCmdOption(cmdopt.ValuelessCmdOption):
    order: int = 20
    name: str = 'nocrashreport'
    cmd_key: str = '--nocrashreport'


@dataclass
class NodefaultSOCmdOption(cmdopt.ValuelessCmdOption):
    order: int = 20
    name: str = 'nodefault'
    cmd_key: str = '--nodefault'


@dataclass
class NologoSOCmdOption(cmdopt.ValuelessCmdOption):
    order: int = 20
    name: str = 'nologo'
    cmd_key: str = '--nologo'


@dataclass
class NofirststartwizardSOCmdOption(cmdopt.ValuelessCmdOption):
    order: int = 20
    name: str = 'nofirststartwizard'
    cmd_key: str = '--nofirststartwizard'


@dataclass
class NorestoreSOCmdOption(cmdopt.ValuelessCmdOption):
    order: int = 20
    name: str = 'norestore'
    cmd_key: str = '--norestore'


@dataclass
class AcceptSOCmdOption(cmdopt.CmdOption):
    """
        It will represent "--accept="socket,host=%s,port=%s,tcpNoDelay=1;urp;StarOffice.ComponentContext""
        It does not check host:port busyness.
    """

    order: int = 30
    name: str = 'accept'
    cmd_key: str = '--accept'
    cmd_value: str = 'socket,host={host},{port}tcpNoDelay=1;urp;StarOffice.ComponentContext'
    host: str = '127.0.0.1'
    port: str = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == 'host':
            if value is None:
                value = self.__class__.host

            if value not in get_local_ips_cached():
                raise ValueError(f'host "{value}" is not local ip address')

        if name == 'port':
            if value is not None:
                try:
                    value = int(value)
                except ValueError as exc:
                    raise ValueError(f'port "{value}" is not valid integer value')
                else:
                    if 0 > value > 65535:
                        raise ValueError(f'port "{value}" neither in range [0..65535] nor None')

        super().__setattr__(name, value)

    def __iter__(self):
        port = ''
        if self.port:
            port = f'port={self.port},'
        yield f'{self.cmd_key}={self.cmd_value.format(host=self.host, port=port)}'


@dataclass
class ConvertToSOCmdOption(cmdopt.CmdOption):
    order: int = 40
    name: str = 'convert_to'
    cmd_key: str = '--convert-to'
    cmd_value: str = 'html'


@dataclass
class ConvertImagesToSOCmdOption(cmdopt.CmdOption):
    order: int = 50
    name: str = 'convert_images_to'
    cmd_key: str = '--convert-images-to'
    cmd_value: str = 'jpg'


@dataclass
class OutdirSOCmdOption(cmdopt.CmdOption):

    order: int = 60
    name: str = 'outdir'
    cmd_key: str = '--outdir'
    cmd_value: str = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == 'cmd_value' and value:
            if value and not Path(value).is_dir():
                raise ValueError(f'directory {value} does not exist')
        super().__setattr__(name, value)


@dataclass
class FileSOCmdOption(cmdopt.KeylessCmdOption):
    order: int = 100
    name: str = 'file'
    cmd_value: str = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == 'cmd_value' and value:
            if value and not Path(value).is_file():
                raise ValueError(f'file {value} does not exist')
        super().__setattr__(name, value)
