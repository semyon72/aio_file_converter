# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: soffice_server.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-17 (y-m-d) 2:27 PM
import functools
import io
import logging
import tempfile
import time
import asyncio
import copy

from dataclasses import dataclass
from typing import Optional, Callable, Generator
from binascii import crc32

import psutil

import cmd_options as cmdopt
import soffice_options as sopt


logger = logging.getLogger(__name__)


def get_sleep_time(max_=30, start=0.75, incr=0.12) -> Generator[float, None, None]:
    # by default it will next sequence
    # [0.56, 0.76, 0.98, 1.23, 1.51, 1.82, 2.16, 2.53, 2.92, 3.35, 3.8, 4.28, 4.8]
    # total time 30.7
    # ! sum of sequence must be greater than self.wait_timeout (max_)

    rest = max_
    c = start
    while rest > 0:
        val = round(c ** 2, 2)
        yield val
        rest -= val
        c = c + incr


def run_once(func, *other):
    """
    It can be used like not parametrized decorator @run_once
    If other exists, it should be used
        somefunc = run_once(f, f1, f2, ....)
        result_f = somefunc(arg_for_f)
        result_f1 = somefunc(arg_for_f1)
        result_f2 = somefunc(arg_for_f2)

        but if list of f, f1, f2, .... is done
        result = somefunc(arg)
        result is None

    :param func:
    :param other: other functions
    :return: function
    """

    def func_gen():
        for f in (func, *other):
            yield f

    fg = func_gen()
    done = False

    def wrapper(*args, **kwargs):
        nonlocal done
        if not done:
            try:
                f = next(fg)
            except StopIteration:
                done = True
            else:
                return f(*args, **kwargs)

    # Looks so as used as decorator
    if not other:
        wrapper = functools.update_wrapper(wrapper, func)

    return wrapper


@dataclass
class ProgramCmdOption(cmdopt.KeylessCmdOption):
    order: int = 0
    name: str = 'program'
    cmd_value: str = 'python3'


@dataclass
class HostCmdOption(cmdopt.CmdOption):
    order: int = 20
    name: str = 'host'
    cmd_key: str = '--bind'
    cmd_value: str = '127.0.0.1'


@dataclass
class PortCmdOption(cmdopt.KeylessCmdOption):
    order: int = 30
    name: str = 'port'
    cmd_value: str = '7800'


class BaseAsyncServer:
    options: Optional[cmdopt.CmdOptions] = cmdopt.CmdOptions(
        ProgramCmdOption(), HostCmdOption(), PortCmdOption()
    )

    wait_timeout = 10

    def __init__(self, host=None, port=None,
                 stdout: Optional[io.StringIO] = None, stderr: Optional[io.StringIO] = None,
                 logger_handler: Optional[logging.Handler] = None) -> None:

        self.options = copy.copy(self.options)

        self._loop = asyncio.get_running_loop()
        self._effective_port: asyncio.Future = self._loop.create_future()
        self._proc: asyncio.Future = self._loop.create_future()
        self._waiters = [self._effective_port, self._proc]
        self._process_task: Optional[asyncio.Task] = None

        self.__server_id = None  # used just for logging
        self.__self_id = crc32(str(id(self)).encode())  # used just for logging

        self.host = host
        self.port = port
        self.stdout = stdout
        self.stderr = stderr

        if not isinstance(logger_handler, logging.Handler):
            exists = [handler for handler in logger.handlers if isinstance(handler, logging.StreamHandler)]
            if not exists:
                logger.addHandler(logging.StreamHandler())
        else:
            logger.addHandler(logger_handler)

    @property
    def proc(self) -> Optional[asyncio.subprocess.Process]:
        return self._proc.result()

    @property
    def host(self):
        return self.options['host'].cmd_value

    @host.setter
    def host(self, value):
        if self._proc.done():
            raise RuntimeError('Changing host, when server is running')

        self.options['host'].cmd_value = value

    @property
    def port(self):
        return self.options['port'].cmd_value

    @port.setter
    def port(self, value):
        if self._proc.done():
            raise RuntimeError('Try to change a port, when server is running')
        self.options['port'].cmd_value = value

    @property
    def effective_port(self):
        result = None
        if self._effective_port.done():
            result = self._effective_port.result()
        return result

    async def get_effective_port(self):
        try:
            await asyncio.wait_for(self._proc, self.wait_timeout)
        except Exception as exc:
            e = RuntimeError('Process is not started yet. Either process or process_background must be used earlier.')
            self._process_exc(exc, e)

        try:
            result = await self._effective_port
        except Exception as exc:
            self._process_exc(exc)
        else:
            return result

    def get_process_task_name(self):
        """
            Returns unified string that contains initial host and port.
        """
        host = self.host or '"..."'
        port = self.effective_port or self.port or '"..."'
        return f'aioSOServer_{self.__self_id}_{host}:{port}_runner'

    def _make_log_message(self, msg='', msg_key: str = 'message') -> list[str]:
        """
             1. run process (self.__server_id is None, self.proc is None)
             2. process created (self.__server_id is None)
             3. effective port is gotten

             now we will have server id _get_log_message(self) - contains
             4. any other message with self.__server_id

         :param msg:
         :return:
         """
        items = [f'##{self.__self_id}##']
        if self.__server_id is None:
            items.append(f'task [{self.get_process_task_name()}]:')
            if not self._proc.done():
                items.append('running')
            else:
                items.append('ran')
                items.append(f'pid: [{self.proc.pid}]')

                if self.effective_port is not None:
                    items.append(f'effective_port: [{self.effective_port}]')
                    items.append(f'cmd: [{self.options}]')
                    self.__server_id = crc32(' '.join(items).encode())
                    items.append(f'sid: [{self.__server_id}]')
        else:
            items.append(f'sid: [{self.__server_id}]:')
            items.append(f'pid: [{self.proc.pid}]')
            items.append(f'port: [{self.effective_port}]')

        if msg:
            items.append(f'{msg_key}: {msg}')

        return items

    def _log_server(self, msg='', msg_key: str = 'message'):
        logger.info(' '.join(self._make_log_message(msg, msg_key)))

    def _process_exc(self, exc: Exception, new_exc: Exception = None):
        if self._proc.done():
            self.proc.terminate()

        if exc:
            for waiter in self._waiters:
                if not waiter.done():
                    waiter.set_exception(exc)
            if new_exc:
                exc.__cause__ = exc
            raise exc

    async def _poll_pipe(self, pipe: asyncio.subprocess.PIPE, out_stream: io.StringIO):
        names = {self.proc.stdout: 'stdout', self.proc.stderr: 'stderr'}

        while True:
            b = await pipe.readline()
            if not b:
                break
            if out_stream is not None:
                out_stream.write(b)
            msg_key = names.get(pipe, 'std...')
            self._log_server(f'{b.decode()[:-1]}', msg_key=msg_key)

    def _make_stdout_stderr_readers(self) -> dict[str, asyncio.Task]:
        readers = {}
        for std_name in ('stdout', 'stderr'):
            proc_stdx = getattr(self.proc, std_name, None)
            if proc_stdx:
                self_stdx = getattr(self, std_name, None)
                task_name = f'{self.get_process_task_name()}_poll_{std_name}'
                task = self._loop.create_task(self._poll_pipe(proc_stdx, self_stdx), name=task_name)
                readers[std_name] = task
        return readers

    def _run_on_start(self, on_start: Optional[Callable] = None):
        if callable(on_start):
            scb_time = time.perf_counter()
            on_start(self)
            cb_time = time.perf_counter() - scb_time
            if time.perf_counter() - scb_time > 1:
                logger.warning(' '.join(
                    self._make_log_message(f'on_start callback is too slow [{round(cb_time, 2)}s]')
                ))

    def _check_port(self):
        if self.port:
            iport = int(self.port)
            conis = [coni for coni in psutil.net_connections() if coni.laddr[1] == iport]
            assert len(conis) < 2, f'Too many ports opened. Probably wrong logic {conis}'
            if conis:
                p = psutil.Process(conis[0].pid)
                raise RuntimeError(f'Port [{iport}] is busy by pid:[{p.pid}] cmd: {p.cmdline()}')

    def _get_effective_port_cmd_compare(self, proc_cmd: list, init_cmd: list):
        lcmp = len(init_cmd) - 1
        return init_cmd[-lcmp:] == proc_cmd[-lcmp:]

    async def _get_effective_port(self):
        if self.proc is None:
            raise RuntimeError('It only works, if process has been created.')

        init_cmd = self.options.args()[1:]

        psi = psutil.Process(self.proc.pid)
        for stime in get_sleep_time(self.wait_timeout):

            efpids = []
            for p in (psi, *psi.children()):
                proc_cmd = p.cmdline()[1:]
                if self._get_effective_port_cmd_compare(proc_cmd, init_cmd):
                    efpids.append(p.pid)

            self._log_server(f'_get_effective_port -> effective_pids: {efpids}')

            las = [coni.laddr[1] for coni in psutil.net_connections() if coni.pid in efpids]
            llas = len(las)
            if llas != 1:
                if llas > 1:
                    logger.error(' '.join(
                        self._make_log_message(f'_get_effective_port-s: {las}')
                    ))
                    port = int(self.port)
                    if port in las:
                        return port
                    # raise RuntimeError(f'can\'t resolve unambiguity the effective port {las}')
                else:
                    self._log_server(f'_get_effective_port -> slept time: {stime}')
                    await asyncio.sleep(stime)
            else:
                self._log_server(f'_get_effective_port: {las}')
                return las[0]

        raise asyncio.TimeoutError(
            f'Unable to get effective port of running server. self_id[{self.__self_id}]'
        )

    async def _create_subprocess(self):
        program, *args = self.options.args()
        return await asyncio.create_subprocess_exec(
            program, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

    async def process(self, on_start: Optional[Callable] = None) -> int:
        self.__server_id = None
        if self._proc.done():
            raise RuntimeError(f'Process is ran already: {self.proc.pid}')

        try:
            self._check_port()
        except Exception as exc:
            self._process_exc(exc)

        self._log_server()

        self._proc.set_result(await self._create_subprocess())
        pipe_readers = {}
        returncode = 256
        try:
            pipe_readers = self._make_stdout_stderr_readers()

            self._log_server(f'trying to get effective port')
            try:
                self._effective_port.set_result(await self._get_effective_port())
            except Exception as exc:
                self._process_exc(exc)
            else:
                self._log_server()

            self._log_server('started')
            self._run_on_start(on_start=on_start)

            for pipe_name, task in pipe_readers.items():
                await task

            returncode = await self.proc.wait()

        except Exception as exc:
            self._process_exc(exc)

        finally:
            if returncode == 256:
                self._process_exc(
                    RuntimeError(
                        f'Abnormal termination.'
                        f' returncode[{returncode}] means await self.proc.wait() did raise not Exception exception'
                    )
                )

            if self._process_task is not None and not self._process_task.done():
                self._process_task.cancel(
                    f'task {self.get_process_task_name()} is done due to returncode [{returncode}]'
                )

            self._log_server(f'stopped with code [{returncode}]')
            msg = 'server task is done'
            for pipe_name, task in pipe_readers.items():
                if not task.done():
                    task.cancel(' '.join(self._make_log_message(msg, f'poll_{pipe_name}_task')))

        return returncode

    def process_background(self) -> asyncio.Task:
        self._process_task = self._loop.create_task(self.process(), name=self.get_process_task_name())
        return self._process_task


@dataclass
class ModuleCmdOption(cmdopt.CmdOption):
    order: int = 10
    name: str = 'module'
    cmd_key: str = '-m'
    cmd_value: str = 'http.server'


class TestHTTPAsyncServer(BaseAsyncServer):

    def __init__(self, host=None, port=None, stdout: Optional[io.StringIO] = None,
                 stderr: Optional[io.StringIO] = None, logger_handler: Optional[logging.Handler] = None) -> None:
        super().__init__(host, port, stdout, stderr, logger_handler)
        self.options.add(ModuleCmdOption())


class SofficeAsyncServer(BaseAsyncServer):

    options = cmdopt.CmdOptions(
        sopt.ProgramSOCmdOption(), sopt.HeadlessSOCmdOption(), sopt.UserProfileDirSOCmdOption(),
        sopt.AcceptSOCmdOption(),
        sopt.InvisibleSOCmdOption(), sopt.NocrashreportSOCmdOption(), sopt.NodefaultSOCmdOption(),
        sopt.NologoSOCmdOption(), sopt.NofirststartwizardSOCmdOption(), sopt.NorestoreSOCmdOption(),
    )

    wait_timeout = 20

    def __init__(self, host=None, port=None, stdout: Optional[io.StringIO] = None, stderr: Optional[io.StringIO] = None,
                 logger_handler: Optional[logging.Handler] = None) -> None:
        super().__init__(host, port, stdout, stderr, logger_handler)
        self._user_profile_dir: Optional[tempfile.TemporaryDirectory] = None

    @property
    def proc(self) -> Optional[asyncio.subprocess.Process]:
        return self._proc.result()

    @property
    def host(self):
        return self.options['accept'].host

    @host.setter
    def host(self, value):
        if self._proc.done():
            raise RuntimeError('Changing host, when server is running')

        self.options['accept'].host = value

    @property
    def port(self):
        return self.options['accept'].port

    @port.setter
    def port(self, value):
        if self._proc.done():
            raise RuntimeError('Try to change a port, when server is running')
        self.options['accept'].port = value

    def _create_user_profile_dir(self):
        if self._user_profile_dir:
            self._user_profile_dir.cleanup()

        pd = tempfile.TemporaryDirectory(prefix='soffice_', suffix=f'.aio_serv')
        self._user_profile_dir = pd
        self._log_server(f'user profile directory: [{pd.name}]')
        self.options['user_profile_dir'].cmd_value = pd.name

    async def _create_subprocess(self):
        self._create_user_profile_dir()

        program, *args = self.options.args()
        return await asyncio.create_subprocess_exec(
            program, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

    async def process(self, on_start: Optional[Callable] = None) -> int:
        try:
            result = await super().process(on_start)
        finally:
            if self._user_profile_dir:
                self._user_profile_dir.cleanup()
        return result


if __name__ == '__main__':

    logger.setLevel(logging.INFO)

    import unoserver.converter as unoconv

    # start_time = time.perf_counter()
    #
    # @run_once
    # def run_callback(serv: SofficeAsyncServer):
    #
    #     print(f'##### pid: {serv.proc.pid}')
    #     print(f'##### port: {serv.effective_port}')
    #     print(f'##### returncode: {serv.proc.returncode}')
    #
    #
    # async def process() -> SofficeAsyncServer:
    #     soservers = (SofficeAsyncServer(), SofficeAsyncServer(), SofficeAsyncServer())
    #
    #     server_tasks = [server.process_background() for server in soservers]
    #     effective_ports = await asyncio.gather(*[server.get_effective_port() for server in soservers])
    #
    #     converter = unoconv.UnoConverter(soservers[0].host, port=soservers[0].effective_port)
    #     src = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/ssl-certificates.odt'
    #     out = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Results/Python/ssl-certificates.html'
    #     converter.convert(inpath=src, outpath=out, convert_to='html')
    #
    #     soserv_with_done_state = []
    #     for task in server_tasks:
    #          soserv_with_done_state.append(await task)
    #
    #     return soserv_with_done_state
    #
    # res = asyncio.run(process(), debug=False)



    # converter = unoconv.UnoConverter('127.0.0.1', port=41249)
    # src = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/ssl-certificates.odt'
    # out = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Results/Pythonaeraerawerawere/ssl-certificates.html'
    # result = converter.convert(inpath=src, outpath=out, convert_to='html')
    # pass



    # test on webserver basis

    async def process() -> TestHTTPAsyncServer:
        soservers = (
            TestHTTPAsyncServer(port='8080'), TestHTTPAsyncServer(port='8081'), TestHTTPAsyncServer(port='8082')
        )
        # soservers = (TestHTTPAsyncServer(port='8080'), )

        server_tasks = [server.process_background() for server in soservers]
        effective_ports = await asyncio.gather(*[server.get_effective_port() for server in soservers])

        soserv_with_done_state = await asyncio.wait(server_tasks)

        return soserv_with_done_state


    res = asyncio.run(process(), debug=True)
