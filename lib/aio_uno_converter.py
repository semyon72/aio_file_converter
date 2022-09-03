# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: aio_uno_converter.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-30 (y-m-d) 3:17 PM
import asyncio
import time
from pathlib import Path
from typing import Optional, Union

from definitions import AsyncQueueGetProcessable, FileInfo
from soffice_server import SofficeAsyncServer
from unoserver.converter import UnoConverter


class AsyncSOUnoConverter(AsyncQueueGetProcessable):

    timeout = 20

    def __init__(self, outdir: Union[str, Path], convert_to: str = 'html') -> None:
        self._queue: Optional[asyncio.Queue] = None
        self.outdir: Path = outdir if isinstance(outdir, Path) else Path(outdir)
        if not self.outdir.exists():
            self.outdir.mkdir()
        self._soffice_server: Optional[SofficeAsyncServer] = None
        self._soffice_server_task: Optional[asyncio.Task] = None
        self._converter = None
        self.convert_to = convert_to

    def get_converter(self) -> UnoConverter:
        if self._converter is None:
            self._converter = UnoConverter(
                interface=self._soffice_server.host,
                port=self._soffice_server.effective_port
            )
        return self._converter

    async def _get_server(self):
        if self._soffice_server is None:
            self._soffice_server = SofficeAsyncServer()
            self._soffice_server_task = self._soffice_server.process_background()
            port = await self._soffice_server.get_effective_port()

        return self._soffice_server

    async def _finalize_server(self, ):
        self._soffice_server.proc.terminate()
        try:
            await self._soffice_server_task
        except asyncio.CancelledError as exc:
            pass

    async def _cleanup_queue_on_convert_exc(self, queue: asyncio.Queue, provider_future: asyncio.Task, exc: Exception):
        provider_future.cancel(str(exc))  # in real this is task

        # queued messages dump to unlock external queue.join()
        while not queue.empty():
            queue.get_nowait()
            queue.task_done()

        await provider_future

    async def process(self, queue: asyncio.Queue, provider_task: asyncio.Task):
        result = []
        await self._get_server()
        while not provider_task.done() or not queue.empty():
            try:
                file_info: FileInfo = queue.get_nowait()
            except asyncio.QueueEmpty as exc:
                await asyncio.sleep(0)
                continue

            stime = time.perf_counter()
            converter = self.get_converter()
            inpath = file_info.home / file_info.file
            outfile = file_info.file.with_suffix(f'.{self.convert_to}')
            outpath = self.outdir / outfile
            outpath.parent.mkdir(parents=True, exist_ok=True)
            try:
                converter.convert(inpath=inpath, outpath=str(outpath), convert_to=self.convert_to)
            except RuntimeError as exc:
                # need close server and tasks
                await self._finalize_server()
                try:
                    await self._cleanup_queue_on_convert_exc(queue, provider_task, exc)
                except asyncio.CancelledError:
                    pass
                raise exc

            else:
                queue.task_done()
                result.append(f'"{file_info.file}" -> "{outfile}" [done in {time.perf_counter() - stime:.2f}]')

            await asyncio.sleep(0)

        await self._finalize_server()

        return result
