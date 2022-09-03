# IDE: PyCharm
# Project: aio_post_tools
# Path: experiments
# File: soffice_tools.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-14 (y-m-d) 2:19 PM

# Helpful links. Also, see description of SofficeHeadlessSubprocessConverter
# https://help.libreoffice.org/6.2/he/text/shared/guide/start_parameters.html - Starting LibreOffice Software With Parameters
# https://api.libreoffice.org/ - LibreOffice 7.3 API Documentation
# https://git.libreoffice.org/sdk-examples/+/HEAD/ - Examples
# https://git.libreoffice.org/sdk-examples/+/HEAD/MiscFunctionsPyUNOPython/runner.py - LibreOfficeRunner
# https://github.com/unoconv/unoconv - Python unoconv Git page
# https://github.com/unoconv/unoconv/blob/master/unoconv - Python unoconv source code on Git (one file contains all code)
import concurrent.futures
import tempfile
import time
from pathlib import Path
from typing import Iterable, Any, NamedTuple, Union, Optional
import asyncio
from urllib import request

from definitions import AsyncQueueGetProcessable, FileInfo


class PopenResult(NamedTuple):
    out: str
    err: str
    return_code: int
    timeout_expired: bool
    pid: int

    @property
    def is_error(self):
        return self.return_code != 0


class SofficeHeadlessSubprocessConverter:
    """
        !!! This converter works properly, successful and not successful at same time.
        Not successful, because, looks like soffice has bug
        when it makes conversion simultaneous from different subprocesses.
        For example, Source had 11 *.odt files but after conversion were gotten only 6.
        Process information on last 5 *.odt files returned a return code - 1
        In common case, exit status (code) = 1 is
        General errors, Miscellaneous errors, such as "divide by zero" and other Impermissible operations.

        Asynchronous process() method runs the execution of command like
        'soffice --headless --convert-to 'html' --convert-images-to 'jpg' --outdir '..../dest_dir' '..../some_file.odt')
        inside a subprocess. It returns PopenResult information.

        UPD:

        Key to resolve this issue is -env:UserInstallation=file:///tmp/delete_me_#{timestamp} parameter.
        It allows to run many the "different" processes that will not be overlap

        https://wiki.documentfoundation.org/UserProfile - look at
        'Quick test for corrupted profiles: use a temporary, new user profile' and 'Reusing user profiles'
        https://stackoverflow.com/questions/59987439/running-libreoffice-as-a-service - discussion
        https://ask.libreoffice.org/t/multiple-instances-for-c-automation/2114 - answer that was pointed inside previous link

        As example to resolve this issue, look at:

        https://github.com/unoconv/unoserver - project
        It looks like a separation https://github.com/unoconv/unoconv into 2 parts, server and converter.
        Also, it seems more fresh and flexible for using as python's module.

        https://github.com/unoconv/unoserver/blob/master/src/unoserver/server.py - runs soffise subprocess for listening
        It allows to run the multiple standalone processes
        https://github.com/unoconv/unoserver/blob/master/src/unoserver/converter.py -
        most interesting part as example how it works and separate using as module.
        For example, can be used UnoConverter class

    """

    # This code incompatible with version (probable early Python 3.7) which not supports order insertion
    popen_args: dict[str, Any] = {
        'headless': ['--headless'],
        # next commented is not mandatory
        # 'invisible': ["--invisible"],
        # 'nocrashreport': ["--nocrashreport"],
        # 'nodefault': ["--nodefault"],
        # 'nologo': ["--nologo"],
        # 'nofirststartwizard': ["--nofirststartwizard"],
        # 'norestore': ["--norestore"],
        'convert_to': ['--convert-to', 'html'],
        'convert_images_to': ['--convert-images-to', 'jpg'],
        'outdir': ['--outdir', None],
        'file': [None],  # mandatory, should be last
    }

    def __init__(self, file: Union[str, Path], outdir: Union[str, Path]) -> None:
        self.program: str = 'soffice'
        self.popen_args = dict(self.popen_args)
        self.file = file
        self.outdir = outdir

    def __set_file_outdir(self, key, value, test_func_name, msg_arg):
        if value is not None:
            if not isinstance(value, Path):
                value = Path(value)
            test_func = getattr(value, test_func_name)
            if not test_func():
                raise ValueError(f'{msg_arg} "{value}" does not exist.')
            value = str(value)

        self.set_arg(key, value, replace=True)

    @property
    def file(self) -> str:
        return self.get_arg('file')[0]

    @file.setter
    def file(self, value):
        # fix for weird behaviour of soffice if the file part is not last one
        if 'file' in self.popen_args and next(reversed(self.popen_args)) != 'file':
            self.__set_file_outdir('file', None, 'is_file', 'file')

        self.__set_file_outdir('file', value, 'is_file', 'file')

    @property
    def outdir(self) -> str:
        return self.get_arg('outdir')[1]

    @outdir.setter
    def outdir(self, value):
        self.__set_file_outdir('outdir', value, 'is_dir', 'directory')
        self.popen_args['outdir'].insert(0, '--outdir')

    def get_arg(self, key) -> list:
        return self.popen_args[key]

    def set_arg(self, key, value, replace=True) -> None:
        if value is None:
            del self.popen_args[key]
            return

        if not isinstance(value, Iterable) or isinstance(value, str):
            value = [str(value)]

        if replace:
            self.popen_args[key] = value
        else:
            self.popen_args.setdefault(key, []).extend(value)

    @property
    def args(self) -> list:
        result = []

        # fix for weird behaviour of soffice if the file part is not last one
        self.file = self.file

        for key, value in self.popen_args.items():
            action = result.append
            if isinstance(value, Iterable):
                action = result.extend
            action(value)

        return result

    async def process(self, timeout=None) -> PopenResult:
        time_expired, out, err, returncode, pid = False, '', '', None, None
        try:
            proc = await asyncio.create_subprocess_exec(
                    self.program, *self.args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            pid = proc.pid

            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out = stdout_data.decode()
            err = stderr_data.decode()
            returncode = proc.returncode

        except asyncio.exceptions.TimeoutError as exc:
            time_expired = True

        result = PopenResult(
            out=out,
            err=err,
            return_code=returncode,
            timeout_expired=time_expired,
            pid=pid
        )

        return result


class SafeSofficeHeadlessSubprocessConverter(SofficeHeadlessSubprocessConverter):

    popen_args: dict[str, Any] = {
        'headless': ['--headless'],
        'user_profile_dir': [None],  # it should be like file:///directory/path
        'convert_to': ['--convert-to', 'html'],
        'convert_images_to': ['--convert-images-to', 'jpg'],
        'outdir': ['--outdir', None],
        'file': [None],  # mandatory, should be last
    }

    @property
    def user_profile_dir(self):
        return self.get_arg('user_profile_dir')

    @user_profile_dir.setter
    def user_profile_dir(self, value):
        value = request.pathname2url(value)
        self.set_arg('user_profile_dir', f'-env:UserInstallation=file://{value}')

    async def process(self, timeout=None) -> PopenResult:
        with tempfile.TemporaryDirectory(prefix='soffice_', suffix='.up') as tmpdir:
            self.user_profile_dir = tmpdir
            return await super().process(timeout)


class AsyncSOSubprocessConverter(AsyncQueueGetProcessable):

    timeout = 20

    def __init__(self, outdir: Union[str, Path], convert_to: str = 'html') -> None:
        self._queue: Optional[asyncio.Queue] = None
        self.outdir: Path = outdir if isinstance(outdir, Path) else Path(outdir)
        if not self.outdir.exists():
            self.outdir.mkdir()
        self._converter = None
        self.convert_to = convert_to

    def get_converter(self, file: Path) -> SafeSofficeHeadlessSubprocessConverter:
        if self._converter is None:
            self._converter = SafeSofficeHeadlessSubprocessConverter(file=str(file), outdir=self.outdir)
            arg_convert_to = self._converter.get_arg('convert_to')
            arg_convert_to[1] = self.convert_to
            self._converter.set_arg('convert_to', arg_convert_to)
        else:
            self._converter.file = file
        return self._converter

    async def process(self, queue: asyncio.Queue, provider_task: asyncio.Task):
        result = []
        while not queue.empty():
            try:
                file_info: FileInfo = await queue.get()
            except asyncio.QueueEmpty as exc:
                break
            else:
                stime = time.perf_counter()
                with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
                    converter = self.get_converter(file_info.home / file_info.file)
                    outdir_path = (self.outdir / file_info.file).parent
                    outdir_path.mkdir(parents=True, exist_ok=True)
                    converter.outdir = str(outdir_path)
                    res = await converter.process(timeout=self.timeout)

                queue.task_done()
                result.append(f'{file_info.file} [done in {time.perf_counter() - stime:.2f}]: {res}')

        return result


if __name__ == '__main__':
    file = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/coroutine.odt'
    outdir = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Results/Python/asyncio'

    proc_coro = SofficeHeadlessSubprocessConverter(file, outdir).process()
    result = asyncio.run(proc_coro, debug=True)
    print(f'##### Result: {result}')

    safe_proc_coro = SafeSofficeHeadlessSubprocessConverter(file, outdir).process()
    result = asyncio.run(safe_proc_coro, debug=True)
    print(f'##### Result: {result}')
