import logging
import xmltodict

from .base_session import BaseSession
from .exceptions import raise_requests_error

log = logging.getLogger(__name__)


class ClientSession(BaseSession):
    """Methods for clients."""
    def __init__(self, cache_methods=None, *args, **kwargs):
        cache_methods = cache_methods or ['get_client',
                                          'get_client_properties',
                                          'get_clients']
        super(ClientSession, self).__init__(cache_methods=cache_methods, *args, **kwargs)

    def get_client(self, client_id):
        """Get client.

        Args:
            client_id (str): client id

        Returns:
            dict: client
        """
        if isinstance(client_id, int):
            log.warning('deprecated: client_id support for int for backward compatibility only')
            client_id = str(client_id)
        try:
            try:
                return [c for c in self.get_clients()
                        if str(c['client']['clientEntity']['clientId']) == client_id][0]
            except KeyError:
                # support previous Commvault api versions
                return [c for c in self.get_clients()
                        if str(c['client']['clientEntity']['@clientId']) == client_id][0]
        except IndexError:
            msg = 'Client {} not in client list.'.format(client_id)
            raise_requests_error(404, msg)

    def get_client_properties(self, client_id):
        """Get client properties.

        This call sometimes replies in XML, because who cares about
        Accept headers right. So, we must take the reply in XML and
        convert it to JSON to maintain sanity.

        Args:
            client_id (str): client id

        Returns:
            dict: client properties
        """
        if isinstance(client_id, int):
            log.warning('deprecated: client_id support for int for backward compatibility only')
            client_id = str(client_id)
        path = 'Client/{}'.format(client_id)
        res = self.request('GET', path)
        # If you are using a < v10 SP12 this call will respond in
        # xml even though we are requesting json.
        if not res.json():
            # turn wrong xml into json
            data = xmltodict.parse(res.text)
        else:
            data = res.json()
        try:
            props = data['clientProperties']
        except KeyError:
            # support previous Commvault api versions
            props = data['App_GetClientPropertiesResponse']['clientProperties']
        if not props:
            msg = 'No client properties found for client {}'.format(client_id)
            raise_requests_error(404, msg)
        return props

    def get_clients(self):
        """Get clients.

        Returns:
            list: clients
        """
        path = 'Client'
        res = self.request('GET', path)
        data = res.json()
        try:
            clients = data['clientProperties']
        except KeyError:
            # support previous Commvault api versions
            clients = data['App_GetClientPropertiesResponse']['clientProperties']
        if not clients:
            msg = 'No clients found in Commvault'
            raise_requests_error(404, msg)
        return clients
