# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: file_provider.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-13 (y-m-d) 1:49 PM
import asyncio
import logging
import os
from enum import Enum, auto
from pathlib import Path
from typing import Iterable, Callable, Generator, Iterator, Optional

from definitions import FileInfo, AsyncQueuePutProcessable


logger = logging.getLogger(__name__)


class ResultPathType(Enum):
    ABSOLUTE = auto()
    AS_IS = auto()
    RELATIVE_TO_HOME = auto()


class FileProvider(Iterable):
    """
        TODO: Rewrite all

        Filters facility has Deny logic if filters_allow is empty list then no one file will accepted.
        Added callback function(obj_getFiles, currentFileOrDir) you should accept or reject it,
        returning True for accept. If no one callback function does not return True this file/dir rejected.
        By default filters_allow contain one callback that accept all files and directories that
        don't start from '.' (hidden files/dirs)

        But if need more customize it then this callback can be removed by [] or changed
        objGetFiles.filters_allow = [someCallBack, someCallBack]
        for file in objGetFiles:
            print(file)

        If need to return it back
        objGetFiles.filters_allow = [objGetFiles._default_filter] # or [GetFiles._default_filter]
        for file in objGetFiles:
            print(file)

        filter callback has next signature - callable(obj_getFiles, currentFileOrDir)
        where obj_getFiles - current instance of GetFiles and currentFileOrDir - real path of current directory/file
        that will be included in final list if callback returns True.
        Note if currentFileOrDir is directory and callback not returns True this directory will be skip from traverse,
        include all files and subdirectories. That's why, sometimes useful to split logic into something like

            if os.path.isdir(file):
                if not os.path.basename(file).startswith('.'):
                    return True
            else: # file
                return True

    """
    _home: Path = None
    _filters: list[Callable] = None
    _result_path_type: ResultPathType = ResultPathType.AS_IS
    __duplicates_due_to_symbolic_links = None

    def __init__(self, home='.', result_path_type=ResultPathType.AS_IS, filters: list[Callable] = None) -> None:
        if not filters:
            filters = [type(self)._default_filter]

        self.filters = filters
        self.home = home
        self.result_path_type = result_path_type
        super().__init__()

    @property
    def home(self) -> Path:
        return self._home

    @home.setter
    def home(self, path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError('The home property must point to an existing directory or file.')
        self._home = path

    @property
    def result_path_type(self) -> ResultPathType:
        return self._result_path_type

    @result_path_type.setter
    def result_path_type(self, value: ResultPathType):
        if value not in ResultPathType:
            raise ValueError(f'value should be one of {["ResultPathType."+rpt.name for rpt in list(ResultPathType)]}')
        self._result_path_type = value

    @staticmethod
    def _default_filter(path):
        if not isinstance(path, Path):
            path = Path(path)

        res = [p for p in Path(path).resolve().parts if p.startswith('.')]
        if len(res) > 0:
            return False

    @property
    def filters(self) -> list[Callable]:
        return self._filters

    @filters.setter
    def filters(self, filters: list[Callable]):
        filters = list(filters)
        if len([f for f in filters if not callable(f)]) > 0:
            raise ValueError('each filter should be callable')
        self._filters = filters

    def filter(self, path) -> bool:
        """
            By default it allows all logic.
            In other words, if filters is empty list or no filters that return True or False it will return True

            Makes traverse through the filters.
            If filter returns not None then traversing breaks.

            path - can be either file, dir or symlink.
            This means each filter callable Callable[Path] -> Union[None, bool] should test it itself

            This is used inside of the iterator logic.
            If filter returns True for the path then path will included into result of files.
            Otherwise will be excluded. Same for directories, but with little subtlety
            - all content of directory will be excluded from traversing at all.
            But for end user, this is almost same.
        """
        if not isinstance(path, Path):
            path = Path(path)

        for f in self.filters:
            result = f(path)
            if result is True or result is False:
                return result

        return True

    def __filter_dirs(self, dirs: list[str], root: str):
        """
            Removes directory from dirs if filter does not allow it
        """
        dlen = len(dirs)
        for i in range(dlen-1, -1, -1):  # walk reverse
            dpath = Path(root) / dirs[i]
            if self.filter(dpath) is False:
                dirs.pop(i)

    @property
    def duplicates_due_to_symbolic_links(self) -> Optional[dict[Path, list[Path]]]:
        return self.__duplicates_due_to_symbolic_links

    def _get_files(self) -> Generator[Path, None, None]:

        def is_symlink_processed(path: Path, processed_abspath_path: dict[Path, list[Path]]):
            abs_path = path.resolve()
            if abs_path in processed_abspath_path:
                processed_abspath_path[abs_path].append(path)
                return True

            if path.is_symlink():
                processed_abspath_path.setdefault(abs_path, []).append(path)

            return False

        self.__duplicates_due_to_symbolic_links = {}  # dict of abspath -> [path, path] duplicates due to symbolic links
        if self.home.is_file():
            yield self.home
        else:
            for root, dirs, files in os.walk(str(self.home), followlinks=True):
                # root is the concatenated root from previous step + each dir from dirs on next step.
                # but on the first step is the root that passed into os.walk

                root_path = Path(root)
                if is_symlink_processed(root_path, self.__duplicates_due_to_symbolic_links):
                    # skip walking through internal processed dirs too
                    dirs.clear()
                    continue

                # remove from dirs the dirs which didn't allow by filter
                self.__filter_dirs(dirs, str(root_path))

                for file in files:
                    file_path = root_path / file

                    # check symlink if it points in already processed file
                    if is_symlink_processed(file_path, self.__duplicates_due_to_symbolic_links):
                        # skip walking through internal processed dirs too
                        continue

                    if self.filter(file_path):
                        res = file_path.relative_to(self.home)
                        if self.result_path_type == ResultPathType.AS_IS:
                            res = file_path
                        elif self.result_path_type == ResultPathType.ABSOLUTE:
                            res = file_path.resolve()
                        elif self.result_path_type == ResultPathType.RELATIVE_TO_HOME:
                            pass

                        yield res

    def __iter__(self) -> Iterator:
        for res_path in self._get_files():
            yield str(res_path)


class AsyncFileProvider(FileProvider, AsyncQueuePutProcessable):

    def __init__(self, home='.', result_path_type=ResultPathType.AS_IS, filters: list[Callable] = None,
                 logger_handler: Optional[logging.Handler] = None) -> None:
        super().__init__(home, result_path_type, filters)

        if not isinstance(logger_handler, logging.Handler):
            exists = [handler for handler in logger.handlers if isinstance(handler, logging.StreamHandler)]
            if not exists:
                logger.addHandler(logging.StreamHandler())
        else:
            logger.addHandler(logger_handler)

    async def process(self, queue: asyncio.Queue):
        cimsg = f'##{self.__class__.__name__}.process()##:'
        cnt = 0
        logger.info(f'{cimsg} started')
        try:
            for file in self._get_files():  # file is path but depends from provider.result_path_type
                fi = FileInfo(self.home, file)
                logger.debug(f'{cimsg} trying put in queue: {fi}')
                await queue.put(fi)
                logger.info(f'{cimsg} file are queued: {fi} ')
                cnt += 1
        except asyncio.CancelledError as exc:
            logger.info(f'{cimsg} cancelled due to: {exc}')
            raise
        else:
            logger.info(f'{cimsg} done, processed: [{cnt}] files')
