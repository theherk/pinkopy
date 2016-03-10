import unittest
import uuid

import pytest
import requests

from pinkopy import exceptions
from pinkopy.exceptions import PinkopyError


class TestPinkopyError(unittest.TestCase):
    msg = str(uuid.uuid4())
    try:
        raise PinkopyError(msg)
    except PinkopyError as e:
        assert msg == e.args[0]


class TestModuleMethods(unittest.TestCase):
    def test_raise_requests_error(self):
        msg = str(uuid.uuid4())
        status_code = str(uuid.uuid4())
        try:
            with pytest.raises(requests.HTTPError):
                exceptions.raise_requests_error(status_code, msg)
        except requests.HTTPError as e:
            assert msg == e.args[0]

if __name__ == '__main__':
    unittest.main()
