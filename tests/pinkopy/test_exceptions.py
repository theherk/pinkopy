import unittest

import pytest
import requests

from pinkopy import exceptions
from pinkopy.exceptions import PinkopyError
from tests.pinkopy import test_helper


class TestPinkopyError(unittest.TestCase):
    msg = test_helper.get_uuid()
    try:
        raise PinkopyError(msg)
    except PinkopyError as e:
        assert msg == e.args[0]


class TestModuleMethods(unittest.TestCase):
    def test_raise_requests_error(self):
        msg = test_helper.get_uuid()
        status_code = test_helper.get_uuid()
        try:
            with pytest.raises(requests.HTTPError):
                exceptions.raise_requests_error(status_code, msg)
        except requests.HTTPError as e:
            assert msg == e.args[0]

if __name__ == '__main__':
    unittest.main()
