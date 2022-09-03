# IDE: PyCharm
# Project: aio_post_tools
# Path: ${DIR_PATH}
# File: ${FILE_NAME}
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-08-16 (y-m-d) 4:42 PM
from pathlib import Path
from unittest import TestCase
from urllib import request

import lib.soffice_options as sopt


class Test(TestCase):

    def _test_has_attrs(self, obj, *attrs):
        for attr in attrs:
            self.assertTrue(hasattr(obj, attr))

    def _test_has_no_attrs(self, obj, *attrs):
        for attr in attrs:
            with self.assertRaises(AttributeError) as exc:
                getattr(obj, attr)

    def test_socmd_option_base(self):
        opt = sopt.cmdopt.CmdOptionBase(30, 'orderkjjkhjhjkhjk')
        self._test_has_attrs(opt, 'name', 'order')
        self._test_has_no_attrs(opt, 'cmd_key', 'cmd_value')

    def test_valueless_socmd_option(self):
        opt = sopt.cmdopt.ValuelessCmdOption(30, 'namehkjhkjhjk', 'cmd_keyjhjhkjhjkhkj')
        self._test_has_attrs(opt, 'name', 'order', 'cmd_key')
        self._test_has_no_attrs(opt, 'cmd_value')

    def test_keyless_cmd_option(self):
        opt = sopt.cmdopt.KeylessCmdOption(30, 'namehkjhkjhjk', 'cmd_valuejhjhkjhjkhkj')
        self._test_has_attrs(opt, 'name', 'order', 'cmd_value')
        self._test_has_no_attrs(opt, 'cmd_key')

    def test_cmd_option(self):
        opt = sopt.cmdopt.CmdOption(30, 'namehkjhkjhjk', 'cmd_keyjhjhkjhjkhkj', 'cmd_valuejhjhkjhjkhkj')
        self._test_has_attrs(opt, 'name', 'order', 'cmd_key', 'cmd_value')
        self._test_has_no_attrs(opt)

    def test_program_socmd_option(self):
        opt = sopt.ProgramSOCmdOption()
        self.assertTupleEqual(opt.args(), ('soffice', ))

    def test_headless_socmd_option(self):
        opt = sopt.HeadlessSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--headless', ))

    def test_invisible_socmd_option(self):
        opt = sopt.InvisibleSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--invisible', ))

    def test_nocrashreport_socmd_option(self):
        opt = sopt.NocrashreportSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--nocrashreport', ))

    def test_nodefault_socmd_option(self):
        opt = sopt.NodefaultSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--nodefault', ))

    def test_nologo_socmd_option(self):
        opt = sopt.NologoSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--nologo', ))

    def test_nofirststartwizard_socmd_option(self):
        opt = sopt.NofirststartwizardSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--nofirststartwizard', ))

    def test_norestore_socmd_option(self):
        opt = sopt.NorestoreSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--norestore', ))

    def test_user_profile_dir_socmd_option(self):
        opt = sopt.UserProfileDirSOCmdOption()
        self.assertTupleEqual(tuple(), opt.args())
        with self.assertRaises(ValueError) as exc:
            opt.cmd_value = __file__
        self.assertEqual(f'directory {__file__} does not exist', exc.exception.args[0])
        dir = Path(__file__).parent
        opt.cmd_value = dir
        self.assertTupleEqual((f'-env:UserInstallation=file://{request.pathname2url(str(dir))}', ), opt.args())

    def test_convert_to_socmd_option(self):
        opt = sopt.ConvertToSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--convert-to', 'html'))
        opt.cmd_value = 'pdf'
        self.assertTupleEqual(opt.args(), ('--convert-to', 'pdf'))
        opt.cmd_value = None
        self.assertTupleEqual(opt.args(), tuple())

    def test_convert_images_to_socmd_option(self):
        opt = sopt.ConvertImagesToSOCmdOption()
        self.assertTupleEqual(opt.args(), ('--convert-images-to', 'jpg'))
        opt.cmd_value = 'png'
        self.assertTupleEqual(opt.args(), ('--convert-images-to', 'png'))
        opt.cmd_value = None
        self.assertTupleEqual(opt.args(), tuple())

    def test_outdir_socmd_option(self):
        opt = sopt.OutdirSOCmdOption()

        self.assertTupleEqual(tuple(), opt.args())

        with self.assertRaises(ValueError) as exc:
            opt.cmd_value = __file__
        self.assertEqual(f'directory {__file__} does not exist', exc.exception.args[0])

        dir = str(Path(__file__).parent)
        opt.cmd_value = dir
        self.assertTupleEqual(('--outdir', str(dir)), opt.args())

        opt.cmd_value = None
        self.assertTupleEqual(tuple(), opt.args())

    def test_file_socmd_option(self):
        opt = sopt.FileSOCmdOption()
        self.assertTupleEqual(tuple(), opt.args())

        dir = str(Path(__file__).parent)
        with self.assertRaises(ValueError) as exc:
            opt.cmd_value = dir

        self.assertEqual(f'file {dir} does not exist', exc.exception.args[0])

        opt.cmd_value = __file__
        self.assertTupleEqual((__file__, ), opt.args())

        opt.cmd_value = None
        self.assertTupleEqual(tuple(), opt.args())

    def test_accept_socmd_option(self):
        res = '--accept=socket,host=%s,%stcpNoDelay=1;urp;StarOffice.ComponentContext'

        opt = sopt.AcceptSOCmdOption()
        self.assertTupleEqual((res % ('127.0.0.1', ''), ), opt.args())

        with self.assertRaises(ValueError) as exc:
            opt.host = 'dfasdfad'

        opt.host = '192.168.23.23'
        self.assertTupleEqual((res % ('192.168.23.23', ''), ), opt.args())

        opt.host = None
        self.assertTupleEqual((res % ('127.0.0.1', ''), ), opt.args())

        opt.host = '192.168.23.23'
        self.assertTupleEqual((res % ('192.168.23.23', ''), ), opt.args())

        with self.assertRaises(ValueError) as exc:
            opt.port = 'ddd'

        opt.port = 34556
        self.assertTupleEqual((res % ('192.168.23.23', f'port={opt.port},'),), opt.args())

    def test_cmd_options(self):
        opts = sopt.cmdopt.CmdOptions()
        self.assertListEqual([], opts.args())

        convert_to = sopt.ConvertToSOCmdOption()
        opts = sopt.cmdopt.CmdOptions(
            convert_to,
            sopt.HeadlessSOCmdOption(),
            sopt.FileSOCmdOption(cmd_value=__file__),
            sopt.NologoSOCmdOption(),
            sopt.ProgramSOCmdOption(),
        )
        self.assertEqual(f'soffice --headless --nologo --convert-to html {__file__}', str(opts))

        opts['file'].cmd_value = None
        self.assertEqual(f'soffice --headless --nologo --convert-to html', str(opts))

        opts['file'].cmd_value=__file__
        self.assertEqual(f'soffice --headless --nologo --convert-to html {__file__}', str(opts))

        convert_to1 = opts.remove('convert_to')
        self.assertEqual(f'soffice --headless --nologo {__file__}', str(opts))
        self.assertEqual(id(convert_to), id(convert_to1))

        self.assertIsNone(opts.remove('convert_to'))
        with self.assertRaises(KeyError) as exc:
            opts['convert_to']

        opts.add(convert_to)
        self.assertEqual(f'soffice --headless --nologo --convert-to html {__file__}', str(opts))

        with self.assertRaises(ValueError) as exc:
            opts.add(convert_to)

        opts.add(convert_to, allow_dup=True)
        self.assertEqual(f'soffice --headless --nologo --convert-to html --convert-to html {__file__}', str(opts))

        opts.remove('convert_to')
        self.assertEqual(f'soffice --headless --nologo {__file__}', str(opts))

        opts.add(convert_to)
        self.assertEqual(f'soffice --headless --nologo --convert-to html {__file__}', str(opts))

        accept_str = res = '--accept=socket,host=%s,%stcpNoDelay=1;urp;StarOffice.ComponentContext'
        opts.remove('convert_to')
        file_opt = opts.remove('file')

        opts.add(sopt.AcceptSOCmdOption())
        self.assertEqual(f'soffice --headless --nologo {accept_str % ("127.0.0.1", "")}', str(opts))
        port = 34567
        opts['accept'].port = port
        self.assertEqual(f'soffice --headless --nologo {accept_str % ("127.0.0.1", f"port={port},")}', str(opts))


