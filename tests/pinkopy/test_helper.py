import requests_mock
import uuid


def get_uuid():
    return str(uuid.uuid4())


def mock_session(base_session, service='http://' + get_uuid(),
                 user=get_uuid(), pw=get_uuid(), token=get_uuid(),
                 content_type='application/json', clients=get_uuid()
                 ):
    get_payload = {
        'App_GetClientPropertiesResponse': {
            'clientProperties': clients
        }
    }
    post_payload = {
        'DM2ContentIndexing_CheckCredentialResp': {
            '@token': token
        }
    }
    headers = {
        'Accept': content_type,
        'Content-type': content_type
    }
    with requests_mock.mock() as m:
        m.get(service + '/Client', json=get_payload)
        m.post(service + '/Login', headers=headers, json=post_payload)
        session = base_session(service, user, pw)
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
