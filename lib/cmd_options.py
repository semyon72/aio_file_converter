# IDE: PyCharm
# Project: aio_post_tools
# Path: lib
# File: cmd_options.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-28 (y-m-d) 6:12 AM

from dataclasses import dataclass, asdict
from typing import Union, Iterator, Any, Optional, Mapping


@dataclass
class CmdOptionBase:
    order: int
    name: str

    def __iter__(self):
        raise NotImplementedError

    def args(self) -> tuple:
        return tuple(self)


@dataclass
class ValuelessCmdOption(CmdOptionBase):
    cmd_key: str

    def __iter__(self):
        if self.cmd_key:
            yield self.cmd_key


@dataclass
class KeylessCmdOption(CmdOptionBase):
    cmd_value: str

    def __iter__(self):
        if self.cmd_value:
            yield self.cmd_value


@dataclass
class CmdOption(KeylessCmdOption, ValuelessCmdOption):

    def __iter__(self):
        if self.cmd_value:
            if self.cmd_key:
                yield self.cmd_key
            yield self.cmd_value


class CmdOptions(Mapping):

    options: Union[list[CmdOptionBase], tuple[CmdOptionBase]] = list()

    def __init__(self, *options: Optional[CmdOptionBase]) -> None:

        # creates a copy of cls.options (it does not copy an each instance of option)
        # for future manipulations that will not be lead to changing in all instances
        if not options:
            options = self.options.__class__(self.options)

        self.options = []
        for opt in options:
            if not isinstance(opt, CmdOptionBase):
                raise TypeError(f'option {opt!r} should be instance of SOCmdOptionBase')
            self.options.append(opt)

    def __iter__(self) -> Iterator[Any]:
        for opt in sorted(self.options, key=lambda opt: opt.order):
            yield from opt

    def __getitem__(self, opt_name: str) -> Union[CmdOptionBase, list[CmdOptionBase]]:
        res = [opt for opt in self.options if opt_name == opt.name]
        if not res:
            raise KeyError('option with name "{opt_name}" does not found')
        if len(res) == 1:
            return res[0]
        return res

    def __copy__(self):
        opts = []
        for opt in self.options:
            cls = type(opt)
            opts.append(cls(**asdict(opt)))
        return type(self)(*opts)

    def __len__(self) -> int:
        return len(self.options)

    def add(self, opt: CmdOptionBase, allow_dup=False):
        if not isinstance(opt, CmdOptionBase):
            raise TypeError('option is not SOCmdOptionBase instance')

        if opt.name not in self or allow_dup:
            self.options.append(opt)
        else:
            raise ValueError(f'option {opt!r} already exists. Use allow_dup=True to add the duplicates')

    def remove(self, opt_name: str) -> Union[CmdOptionBase, list[CmdOptionBase], None]:
        res = []
        for i in range(len(self.options)-1, -1, -1):  # reverse order
            if opt_name == self.options[i].name:
                res.insert(0, self.options[i])
                del self.options[i]
        lres = len(res)
        if lres == 1:
            return res[0]
        elif lres < 1:
            return None

        return res

    def args(self) -> list:
        return list(self)

    def __str__(self):
        return ' '.join(self.args())
