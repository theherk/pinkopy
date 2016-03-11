import inspect
import unittest

from pinkopy.base_session import BaseSession
from tests.pinkopy import test_helper


class TestBaseSessionMethods(unittest.TestCase):
    def test__init__(self):
        expected = test_helper.mock_session(BaseSession)
        base_session = expected['Session']
        test_helper.validate_base_session(expected, base_session)

    def test__enable_method_cache(self):
        base_session = test_helper.mock_session(BaseSession)['Session']
        for method_name in base_session.cache_methods:
            method = getattr(base_session, method_name)
            assert inspect.isfunction(method.cache_info)

    def test_get_token(self):
        # not yet implemented
        pass

    def test_request(self):
        # not yet implemented
        pass


if __name__ == '__main__':
    unittest.main()
