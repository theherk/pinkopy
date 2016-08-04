import requests_mock


def mock_session(base_session, service=None, user=None, pw=None, token=None,
                 content_type=None, clients=None):
    service = service or 'http://example.com'
    user = user or 'user'
    pw = pw or 'pw'
    token = token or 'token'
    content_type = content_type or 'application/json'
    clients = clients or ['client1', 'client2']
    get_response = {
        'App_GetClientPropertiesResponse': {
            'clientProperties': clients
        }
    }
    post_response = {
        'token': token
    }
    headers = {
        'Accept': content_type,
        'Content-type': content_type
    }
    with requests_mock.mock() as m:
        m.get(service + '/Client', json=get_response)
        m.post(service + '/Login', headers=headers, json=post_response)
        config = {
            'service': service,
            'user': user,
            'pw': pw
        }
        session = base_session(**config)
        test_data = {
            'Clients': clients,
            'Content-type': content_type,
            'Password': pw,
            'Service': service,
            'Session': session,
            'Token': token,
            'User': user
        }
        return test_data


def validate_base_session(expected, actual):
    cache_ttl = 1200
    assert cache_ttl == actual.cache_ttl
    assert expected['Service'] == actual.service
    assert expected['User'] == actual.user
    assert expected['Password'] == actual.pw
    assert expected['Token'] == actual.headers['Authtoken']
    assert expected['Content-type'] == actual.headers['Accept']
    assert expected['Content-type'] == actual.headers['Content-type']
    assert actual.use_cache
