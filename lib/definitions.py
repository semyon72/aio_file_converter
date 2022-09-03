# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: protocols.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-29 (y-m-d) 8:49 AM
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class FileInfo:
    home: Path
    file: Path


class AsyncQueuePutProcessable(Protocol):

    async def process(self, queue: asyncio.Queue):
        raise NotImplementedError


class AsyncQueueGetProcessable(Protocol):

    async def process(self, queue: asyncio.Queue, provider_task: asyncio.Task):
        raise NotImplementedError
