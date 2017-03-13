# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from future.builtins import *  # NOQA @UnusedWildImport
from future.standard_library import hooks
from future.utils import PY2

import os
import unittest
from unittest import skipIf

from vcr import vcr, VCRSystem
from vcr.utils import catch_stdout


with hooks():
    from urllib.request import urlopen


class CoreTestCase(unittest.TestCase):
    """
    Test suite for vcr
    """
    def setUp(self):
        # Directory where the test files are located
        self.path = os.path.join(os.path.dirname(__file__), 'vcrtapes')
        self.temp_test_vcr = os.path.join(self.path, 'test_core.temp_test.vcr')
        self.read_test_vcr = os.path.join(self.path, 'test_core.read_test.vcr')

    def tearDown(self):
        # cleanup temporary files
        try:
            os.remove(self.temp_test_vcr)
        except OSError:
            pass

    def test_connectivity(self):
        # basic network connection test to exclude network issues
        r = urlopen('https://www.python.org/')
        self.assertEqual(r.status, 200)

    def test_playback(self):
        # define function with decorator
        @vcr
        def read_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # run the test
        with catch_stdout() as out:
            read_test()
            self.assertEqual(out.getvalue(), '')

    def test_playback_with_debug(self):
        # define function with decorator
        @vcr(debug=True)
        def read_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # run the test
        with catch_stdout() as out:
            read_test()
            self.assertIn('VCR PLAYBACK', out.getvalue())

    @skipIf(PY2, 'recording in PY2 is not supported')
    def test_record(self):
        # define function with @vcr decorator
        @vcr
        def temp_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # .vcr file should not exist at the moment
        self.assertEqual(os.path.exists(self.temp_test_vcr), False)

        # run the test
        with catch_stdout() as out:
            temp_test()
            self.assertEqual(out.getvalue(), '')

        # .vcr file should now exist
        self.assertEqual(os.path.exists(self.temp_test_vcr), True)

    @skipIf(PY2, 'recording in PY2 is not supported')
    def test_record_with_debug(self):
        # define function with @vcr decorator
        @vcr(debug=True)
        def temp_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # .vcr file should not exist at the moment
        self.assertEqual(os.path.exists(self.temp_test_vcr), False)

        # run the test
        with catch_stdout() as out:
            temp_test()
            self.assertIn('VCR RECORDING', out.getvalue())

        # .vcr file should now exist
        self.assertEqual(os.path.exists(self.temp_test_vcr), True)

    @skipIf(PY2, 'recording in PY2 is not supported')
    def test_life_cycle(self):
        # define function with @vcr decorator and enable debug mode
        @vcr(debug=True)
        def temp_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # an initial run of our little test will start in recording mode
        # and auto-generate a .vcr file - however, this file shouldn't exist at
        # the moment
        self.assertEqual(os.path.exists(self.temp_test_vcr), False)

        # run the test
        with catch_stdout() as out:
            temp_test()
            # debug mode should state its in recording mode
            self.assertIn('VCR RECORDING', out.getvalue())

        # now the .vcr file should exist
        self.assertEqual(os.path.exists(self.temp_test_vcr), True)

        # re-run the test - this time it should be using the recorded file
        with catch_stdout() as out:
            temp_test()
            # debug mode should state its in playback mode
            self.assertIn('VCR PLAYBACK', out.getvalue())

    @skipIf(PY2, 'recording in PY2 is not supported')
    def test_overwrite_true(self):
        # overwrite=True will delete a existing tape and create a new file
        @vcr(overwrite=True)
        def temp_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)
        # run it once
        temp_test()
        # get creation date of tape
        mtime = os.path.getmtime(self.temp_test_vcr)
        # run it again
        temp_test()
        self.assertTrue(os.path.getmtime(self.temp_test_vcr) > mtime)

    @skipIf(PY2, 'recording in PY2 is not supported')
    def test_overwrite_false(self):
        # overwrite=False is default behaviour
        @vcr(overwrite=False)
        def temp_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # run it once
        temp_test()
        # get creation date of tape
        mtime = os.path.getmtime(self.temp_test_vcr)
        # run it again
        temp_test()
        # mtime didn't change as the file has not been overwritten
        self.assertEqual(os.path.getmtime(self.temp_test_vcr), mtime)

    @skipIf(PY2, 'recording in PY2 is not supported')
    def test_tape_name(self):
        @vcr(tape_name='test_core.temp_test.vcr')
        def custom_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # run it once - usually it should generate test_core.custom_test.vcr
        custom_test()
        # check if given tape file exists
        self.assertTrue(os.path.exists(self.temp_test_vcr))


class VCRSystemTestCase(unittest.TestCase):
    """
    Test suite for VCRSystem
    """
    def setUp(self):
        # Directory where the test files are located
        self.path = os.path.join(os.path.dirname(__file__), 'vcrtapes')
        self.temp_test_vcr = os.path.join(self.path, 'test_core.temp_test.vcr')
        self.read_test_vcr = os.path.join(self.path, 'test_core.read_test.vcr')

    def tearDown(self):
        # cleanup temporary files
        try:
            os.remove(self.temp_test_vcr)
        except OSError:
            pass
        # reset to default settings
        VCRSystem.reset()

    def test_debug(self):
        # no debug mode on decorator level
        @vcr
        def read_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # run the test - there should be no output
        with catch_stdout() as out:
            read_test()
            self.assertEqual(out.getvalue(), '')

        # now enable global debug mode
        VCRSystem.debug = True
        # re-run the test
        with catch_stdout() as out:
            read_test()
            self.assertIn('VCR PLAYBACK', out.getvalue())

        # reset
        VCRSystem.reset()
        # re-run the test - again no output
        with catch_stdout() as out:
            read_test()
            self.assertEqual(out.getvalue(), '')

    @skipIf(PY2, 'recording in PY2 is not supported')
    def test_overwrite(self):
        # no overwrite setting in decorator level
        @vcr
        def temp_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # run it once
        temp_test()
        # get creation date of tape
        mtime = os.path.getmtime(self.temp_test_vcr)
        # run it again
        temp_test()
        # mtime didn't change as the file has not been overwritten
        self.assertEqual(os.path.getmtime(self.temp_test_vcr), mtime)

        # now enable global overwrite mode
        VCRSystem.overwrite = True
        # get current mtime
        mtime = os.path.getmtime(self.temp_test_vcr)
        # re-run the test
        temp_test()
        # mtime did change this time
        self.assertTrue(os.path.getmtime(self.temp_test_vcr) > mtime)

        # reset
        VCRSystem.reset()
        # get current mtime
        mtime = os.path.getmtime(self.temp_test_vcr)
        # run it again
        temp_test()
        # mtime didn't change as the file has not been overwritten
        self.assertEqual(os.path.getmtime(self.temp_test_vcr), mtime)

    def test_disabled(self):
        # no disabled but debug mode on decorator level
        @vcr(debug=True)
        def read_test():
            r = urlopen('https://www.python.org/')
            self.assertEqual(r.status, 200)

        # run the test - there should be output due to debug
        with catch_stdout() as out:
            read_test()
            self.assertIn('VCR PLAYBACK', out.getvalue())

        # now enable disabled mode
        VCRSystem.disabled = True
        # re-run the test - there should be no output
        with catch_stdout() as out:
            read_test()
            self.assertEqual(out.getvalue(), '')

        # reset
        VCRSystem.reset()
        # re-run the test - again output due to debug mode on decorator level
        with catch_stdout() as out:
            read_test()
            self.assertIn('VCR PLAYBACK', out.getvalue())


if __name__ == '__main__':
    unittest.main()