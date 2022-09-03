# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: aio_file_converter.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-12 (y-m-d) 12:27 PM
import abc
import fnmatch
import asyncio
import time
from pathlib import Path
from typing import Union, Optional, Type
import logging

from aio_uno_converter import AsyncSOUnoConverter
from file_provider import ResultPathType, AsyncFileProvider
from definitions import AsyncQueuePutProcessable, AsyncQueueGetProcessable
from soffice_process import AsyncSOSubprocessConverter


"""
    This version has "floating" error (warning). All works (conversion) properly but at the end we got
    
    doc_home = doc_base / 'work/Docs.Partial.from_flash' - 11 files
    
    SOUnoFileConverter(doc_home, doc_target, queue_maxsize=20, workers_number=1)
    
    Exception ignored in: <function BaseSubprocessTransport.__del__ at 0x7f9c2ade5e50>
    Traceback (most recent call last):
      File "/usr/lib/python3.9/asyncio/base_subprocess.py", line 126, in __del__
      File "/usr/lib/python3.9/asyncio/base_subprocess.py", line 104, in close
      File "/usr/lib/python3.9/asyncio/unix_events.py", line 536, in close
      File "/usr/lib/python3.9/asyncio/unix_events.py", line 560, in _close
      File "/usr/lib/python3.9/asyncio/base_events.py", line 746, in call_soon
      File "/usr/lib/python3.9/asyncio/base_events.py", line 510, in _check_closed
    RuntimeError: Event loop is closed
    
    This error related to _UnixReadPipeTransport
    
"""


class SOFileConverterBase(abc.ABC):

    file_provider_class: Type[AsyncQueuePutProcessable] = AsyncFileProvider
    converter_class: Type[AsyncQueueGetProcessable] = None

    def __init__(self, home: Union[str, Path], dest: Union[str, Path], pattern: str = '*.odt', *,
                 queue_maxsize: int = 12, workers_number: int = 3, convert_to='html') -> None:
        self.home = home
        self.dest = dest
        self.pattern: str = pattern
        self.convert_to = convert_to
        self.queue_maxsize = int(queue_maxsize)
        self.workers_number = workers_number

        self._file_provider: Optional[AsyncFileProvider] = None
        self._converters: list[AsyncQueueGetProcessable] = []

    @property
    def home(self) -> Path:
        return self._home

    @home.setter
    def home(self, value: Union[str, Path]):
        self._home = value if isinstance(value, Path) else Path(value)
        if not self._home.is_dir():
            raise ValueError(f'{value} does not exist or is not a directory')

    @property
    def dest(self) -> Path:
        return self._dest

    @dest.setter
    def dest(self, value: Union[str, Path]):
        self._dest = value if isinstance(value, Path) else Path(value)

    @property
    def workers_number(self) -> int:
        return self._workers_number

    def _calc_workers_number(self, value: int) -> int:
        result = 5
        if value < result:
            result = value

        if self.queue_maxsize < 1:
            return result

        items_per_worker = self.queue_maxsize // value
        if items_per_worker < 2:
            return min(result, self.queue_maxsize)
        else:
            return result

    @workers_number.setter
    def workers_number(self, value: int):
        self._workers_number = self._calc_workers_number(value)

    def __set_file_provider_filters(self):

        def odt_filter(file: Path):  # Callback will invoked inside FileProvider
            if file.is_file():
                return fnmatch.fnmatch(file.name, self.pattern)

        if odt_filter not in self._file_provider.filters:
            self._file_provider.filters.append(odt_filter)

    def get_file_provider(self) -> AsyncFileProvider:
        if self._file_provider is None:
            self._file_provider = self.file_provider_class(self.home)
            self._file_provider.result_path_type = ResultPathType.RELATIVE_TO_HOME
            self.__set_file_provider_filters()

        return self._file_provider

    @abc.abstractmethod
    def get_converter(self) -> AsyncQueueGetProcessable:
        raise NotImplementedError

    async def process(self):
        queue = asyncio.Queue(maxsize=self.queue_maxsize)
        loop = asyncio.get_running_loop()

        provider_task = loop.create_task(self.get_file_provider().process(queue), name='FileProvider')

        converter_tasks: list[asyncio.Task] = []
        for i in range(self.workers_number):
            converter_tasks.append(
                loop.create_task(self.get_converter().process(queue, provider_task), name=f'Converter_{i}')
            )

        # to ensure the provider is exhausted and queue is empty
        await provider_task
        await queue.join()

        results = []
        for converter in converter_tasks:
            results.extend(await converter)

        return results


class SOSubprocessFileConverter(SOFileConverterBase):

    file_provider_class: Type[AsyncQueuePutProcessable] = AsyncFileProvider
    converter_class: Type[AsyncQueueGetProcessable] = AsyncSOSubprocessConverter

    def get_converter(self) -> AsyncSOSubprocessConverter:
        if not self._converters:
            self._converters.append(self.converter_class(outdir=self.dest, convert_to=self.convert_to))
        return self._converters[0]


class SOUnoFileConverter(SOFileConverterBase):

    file_provider_class: Type[AsyncQueuePutProcessable] = AsyncFileProvider
    converter_class: Type[AsyncSOUnoConverter] = AsyncSOUnoConverter

    def get_converter(self) -> AsyncSOUnoConverter:
        converter = self.converter_class(outdir=self.dest, convert_to=self.convert_to)
        self._converters.append(converter)
        return converter


if __name__ == '__main__':

    logging.getLogger().setLevel(logging.INFO)

    doc_base = Path(__file__).parent.parent
    # doc_home = doc_base / 'work/Docs.Partial.from_flash'
    doc_home = '/home/ox23/Desktop/Docs/'
    doc_target = doc_base / 'work/Docs.Results'

    ct = time.perf_counter()
    office_converter = SOUnoFileConverter(doc_home, doc_target, queue_maxsize=20, workers_number=3)
    results = asyncio.run(
        office_converter.process(),
        debug=False
    )
    print(f'##### Result: source: "{doc_home}" -> destination: "{doc_target}"', '\n\t', '\n\t'.join(results), sep='')
    print(f'Result time: [{(time.perf_counter()-ct):.2f}]')
