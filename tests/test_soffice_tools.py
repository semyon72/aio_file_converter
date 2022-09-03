# IDE: PyCharm
# Project: aio_post_tools
# Path: ${DIR_PATH}
# File: ${FILE_NAME}
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-15 (y-m-d) 4:25 AM

import asyncio

from unittest import TestCase

from soffice_process import SofficeHeadlessSubprocessConverter, PopenResult


class TestSofficeHeadlessSubprocessConverter(TestCase):

    def setUp(self) -> None:
        self.file = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/coroutine.odt'
        self.outdir = '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Results/Python/asyncio'
        self.converter = SofficeHeadlessSubprocessConverter(self.file, self.outdir)

    def test_set_arg(self):
        convert_to = self.converter.popen_args['convert_to']
        self.assertListEqual(convert_to, ['--convert-to', 'html'])
        self.converter.set_arg('convert_to', None)
        with self.assertRaises(KeyError) as exc:
            self.converter.popen_args['convert_to']

        self.converter.set_arg('convert_to', ['--convert-to', 'pdf'])
        self.assertListEqual(self.converter.popen_args['convert_to'], ['--convert-to', 'pdf'])

    def test_file(self):
        self.assertEqual(self.file, self.converter.file)
        self.assertEqual('file', next(reversed(self.converter.popen_args))) # should be last

        dummy_key, dummy_val = 'ttt', ['ttt value']
        self.converter.popen_args[dummy_key] = [dummy_val]
        self.assertEqual(dummy_key, next(reversed(self.converter.popen_args)))
        self.assertEqual(self.file, self.converter.file)  # still exists but not last
        self.converter.file = self.converter.file # fix, now should be last
        self.assertEqual('file', next(reversed(self.converter.popen_args)))

    def test_outdir(self):
        self.assertEqual(self.outdir, self.converter.outdir)
        self.assertListEqual(['--outdir', self.outdir],self.converter.popen_args['outdir'])
        dummy_value = 'dfadadfadfadfadfa'
        with self.assertRaises(ValueError) as exc:
            self.converter.outdir = dummy_value
        self.assertEqual(str(exc.exception), f'directory "{dummy_value}" does not exist.')

        del self.converter.popen_args['outdir']
        self.converter.outdir = self.outdir
        self.assertListEqual(['--outdir', self.outdir],self.converter.popen_args['outdir'])
        self.assertEqual('outdir', next(reversed(self.converter.popen_args)))

    def test_args(self):
        del self.converter.popen_args['outdir']
        self.converter.outdir = self.outdir
        self.assertListEqual(['--outdir', self.outdir],self.converter.popen_args['outdir'])
        self.assertEqual('outdir', next(reversed(self.converter.popen_args)))

        res_args = self.converter.args
        self.assertEqual(self.file, res_args[-1])
        test_args = ['--headless', '--convert-to', 'html', '--convert-images-to', 'jpg',
                     '--outdir', self.outdir, self.file]
        self.assertListEqual(test_args, res_args)

    def test_process(self):
        proc_coro = self.converter.process()
        result = asyncio.run(proc_coro, debug=True)

        test_result = PopenResult(
            out='convert /home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/coroutine.odt -> /home/ox23/PycharmProjects/aio_post_tools/work/Docs.Results/Python/asyncio/coroutine.html using filter : HTML (StarWriter)\nOverwriting: /home/ox23/PycharmProjects/aio_post_tools/work/Docs.Results/Python/asyncio/coroutine.html\n',
            err='', return_code=0, timeout_expired=False, pid=0)
        self.assertIsInstance(result, PopenResult)
        for key, val in test_result._asdict().items():
            if key == 'pid':
                continue
            self.assertTrue(hasattr(result, key))
            self.assertEqual(getattr(result, key), val)

