import unittest

import pytest
import requests

from pinkopy import exceptions
from pinkopy.exceptions import PinkopyError


class TestPinkopyError(unittest.TestCase):
    def test_pinkopy_error(self):
        status_code, msg = 404, 'NOT FOUND'
        try:
            raise PinkopyError(status_code, msg)
        except PinkopyError as err:
            assert status_code == err.args[0]
            assert msg == err.args[1]


class TestModuleMethods(unittest.TestCase):
    def test_raise_requests_error(self):
        status_code, msg = 404, 'NOT FOUND'
        try:
            with pytest.raises(requests.HTTPError):
                exceptions.raise_requests_error(status_code, msg)
        except requests.HTTPError as err:
            assert status_code == err.args[0]
            assert msg == err.args[1]


if __name__ == '__main__':
    unittest.main()
