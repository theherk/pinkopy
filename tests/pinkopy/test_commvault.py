import unittest

import requests_mock

from pinkopy import CommvaultSession
from tests.pinkopy import test_helper


class TestCommvaultSessionMethods(unittest.TestCase):
    def test__init__(self):
        expected = test_helper.mock_session(CommvaultSession)
        commvault_session = expected['Session']

        # validate shim
        assert commvault_session.get_client == commvault_session.clients.get_client
        assert commvault_session.get_client_properties == commvault_session.clients.get_client_properties
        assert commvault_session.get_clients == commvault_session.clients.get_clients
        assert commvault_session.get_subclients == commvault_session.subclients.get_subclients
        assert commvault_session.get_job_details == commvault_session.jobs.get_job_details
        assert commvault_session.get_job_vmstatus == commvault_session.jobs.get_job_vmstatus
        assert commvault_session.get_jobs == commvault_session.jobs.get_jobs
        assert commvault_session.get_subclient_jobs == commvault_session.jobs.get_subclient_jobs
        assert 'ClientSession' == commvault_session.clients.__class__.__name__
        assert 'JobSession' == commvault_session.jobs.__class__.__name__
        assert 'SubclientSession' == commvault_session.subclients.__class__.__name__
        test_helper.validate_base_session(expected, commvault_session.clients)
        test_helper.validate_base_session(expected, commvault_session.jobs)
        test_helper.validate_base_session(expected, commvault_session.subclients)

    def test__enter__(self):
        session = test_helper.mock_session(CommvaultSession)['Session']
        assert session == session.__enter__()

    def test_logout(self):
        test_data = test_helper.mock_session(CommvaultSession)
        session = test_data['Session']
        with requests_mock.mock() as m:
            service = test_data['Service']
            m.post(service + '/Logout', headers={}, json={})
            result = session.logout()
            assert result is None
            assert session.headers['Authtoken'] is None


if __name__ == '__main__':
    unittest.main()
