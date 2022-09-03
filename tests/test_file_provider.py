# IDE: PyCharm
# Project: aio_post_tools
# Path: ${DIR_PATH}
# File: ${FILE_NAME}
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-13 (y-m-d) 8:20 AM
from unittest import TestCase

from lib.file_provider import FileProvider, ResultPathType
from pathlib import Path


class TestFileProvider(TestCase):

    def setUp(self) -> None:
        self.home_path = '../../py-post-parser/work/'
        self.file_provider = FileProvider()

    def test_home(self):
        self.assertIsInstance(self.file_provider.home, Path)
        self.assertEqual(self.file_provider.home, Path('.'))
        self.file_provider.home = self.home_path
        self.assertEqual(self.file_provider.home, Path(self.home_path))

    def test_result_path_type(self):
        self.assertIn(self.file_provider.result_path_type, ResultPathType)
        self.file_provider.result_path_type = ResultPathType.RELATIVE_TO_HOME
        self.assertEqual(self.file_provider.result_path_type, ResultPathType.RELATIVE_TO_HOME)
        with self.assertRaises(TypeError) as exc:
            self.file_provider.result_path_type = 'ddfsasdf'
        self.assertEqual(str(exc.exception), "unsupported operand type(s) for 'in': 'str' and 'EnumMeta'")

    def test__default_filter(self):
        self.assertIsNone(self.file_provider._default_filter(Path('/kjhkjhjk/lk;l;l;lk;l')))
        self.assertFalse(self.file_provider._default_filter(Path('/kjhkjhjk/.jhhgjhjhg')))

    @staticmethod
    def _test_py_filter(file: Path):
        if file.is_file():
            if file.suffix == '.py':
                return True

    @staticmethod
    def _test_odt_filter(file: Path):
        if file.is_file():
            return file.suffix == '.odt'

    def test_filters(self):
        self.assertIsInstance(self.file_provider.filters, list)
        self.assertEqual(len(self.file_provider.filters), 1)
        self.assertIs(self.file_provider.filters[0], self.file_provider._default_filter)

        self.file_provider.filters.append(self._test_py_filter)
        self.assertEqual(len(self.file_provider.filters), 2)
        self.assertIs(self.file_provider.filters[1], self._test_py_filter)

        self.file_provider.filters = [self._test_py_filter]
        self.assertEqual(len(self.file_provider.filters), 1)
        self.assertIs(self.file_provider.filters[0], self._test_py_filter)

        with self.assertRaises(ValueError) as exc:
            self.file_provider.filters = [self._test_py_filter, 'bad value']
        self.assertEqual('each filter should be callable', str(exc.exception))

    def test_filter(self):
        exists_file = 'work/Docs.Partial.from_flash/Python/libreoffice-export-documents.odt'
        self.file_provider.filters = [self.file_provider._default_filter, self._test_odt_filter]
        self.assertFalse(self.file_provider.filter('.hghghhggh'))
        self.assertTrue(self.file_provider.filter(Path(__file__).parent.parent / exists_file))

    def test__get_files(self):
        # test is tough coupled to directory content
        test_work_dir = '../../py-post-parser/work'
        result = [
            '../../py-post-parser/work/CertBot & Apache.odt',
            '../../py-post-parser/work/lxml.odt',
            '../../py-post-parser/work/open_ssl/OpenSSL create pair keys.odt',
            '../../py-post-parser/work/open_ssl/OpenSSL config files.odt',
            '../../py-post-parser/work/open_ssl/OpenSSL certificate relations.odt',
            '../../py-post-parser/work/aio_post_tools_python/lxml.odt',
            '../../py-post-parser/work/aio_post_tools_python/Python Test broken links.odt',
            '../../py-post-parser/work/aio_post_tools_python/libreoffice-export-documents.odt',
            '../../py-post-parser/work/aio_post_tools_python/subprocess Popen.odt',
            '../../py-post-parser/work/aio_post_tools_python/ssl-certificates.odt',
            '../../py-post-parser/work/aio_post_tools_python/ssl-connection.odt',
            '../../py-post-parser/work/aio_post_tools_python/asyncio/event_loop.odt',
            '../../py-post-parser/work/aio_post_tools_python/asyncio/asyncio_simple_usage.odt',
            '../../py-post-parser/work/aio_post_tools_python/asyncio/generators.odt',
            '../../py-post-parser/work/aio_post_tools_python/asyncio/coroutine.odt',
            '../../py-post-parser/work/aio_post_tools_python/asyncio/asyncio_loop_is_simple_proof.odt',
            '../../py-post-parser/work/Docs/Apache and mod_ssl.odt',
            '../../py-post-parser/work/Docs/Apache mod_macro.odt',
        ]
        self.file_provider.home = test_work_dir
        self.assertEqual('/home/ox23/PycharmProjects/py-post-parser/work', str(self.file_provider.home.resolve()))

        self.file_provider.filters = [self.file_provider._default_filter, self._test_odt_filter]
        self.file_provider.result_path_type = ResultPathType.AS_IS
        self.assertListEqual(result, list(self.file_provider))

        result = [
            'CertBot & Apache.odt', 'lxml.odt', 'open_ssl/OpenSSL create pair keys.odt',
            'open_ssl/OpenSSL config files.odt', 'open_ssl/OpenSSL certificate relations.odt',
            'aio_post_tools_python/lxml.odt', 'aio_post_tools_python/Python Test broken links.odt',
            'aio_post_tools_python/libreoffice-export-documents.odt', 'aio_post_tools_python/subprocess Popen.odt',
            'aio_post_tools_python/ssl-certificates.odt', 'aio_post_tools_python/ssl-connection.odt',
            'aio_post_tools_python/asyncio/event_loop.odt', 'aio_post_tools_python/asyncio/asyncio_simple_usage.odt',
            'aio_post_tools_python/asyncio/generators.odt', 'aio_post_tools_python/asyncio/coroutine.odt',
            'aio_post_tools_python/asyncio/asyncio_loop_is_simple_proof.odt', 'Docs/Apache and mod_ssl.odt',
            'Docs/Apache mod_macro.odt'
        ]
        self.file_provider.result_path_type = ResultPathType.RELATIVE_TO_HOME
        self.assertListEqual(result, list(self.file_provider))

        result = [
            '/home/ox23/PycharmProjects/py-post-parser/work/Docs/CertBot & Apache.odt',
            '/home/ox23/PycharmProjects/py-post-parser/work/lxml.odt',
            '/home/ox23/PycharmProjects/py-post-parser/work/Docs/OpenSSL/OpenSSL create pair keys.odt',
            '/home/ox23/PycharmProjects/py-post-parser/work/Docs/OpenSSL/OpenSSL config files.odt',
            '/home/ox23/PycharmProjects/py-post-parser/work/Docs/OpenSSL/OpenSSL certificate relations.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/lxml.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/Python Test broken links.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/libreoffice-export-documents.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/subprocess Popen.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/ssl-certificates.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/ssl-connection.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/event_loop.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/asyncio_simple_usage.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/generators.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/coroutine.odt',
            '/home/ox23/PycharmProjects/aio_post_tools/work/Docs.Partial.from_flash/Python/asyncio/asyncio_loop_is_simple_proof.odt',
            '/home/ox23/PycharmProjects/py-post-parser/work/Docs/Apache and mod_ssl.odt',
            '/home/ox23/PycharmProjects/py-post-parser/work/Docs/Apache mod_macro.odt'
        ]

        self.file_provider.result_path_type = ResultPathType.ABSOLUTE
        self.assertListEqual(result, list(self.file_provider))

