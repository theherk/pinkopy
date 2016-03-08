import logging
import requests

log = logging.getLogger(__name__)


class PinkopyError(Exception):
    """pinkopy error.

    Error to be raised when an unexpected condition arises in pinkopy.
    """
    pass


def raise_requests_error(status_code, msg):
    """Raise a requests error.

    Commvault is not smart enough to return the proper error,
    specifically in the case of 404.
    """
    log.error(msg)
    res = requests.Response()
    res.status_code = status_code
    err = requests.HTTPError(msg)
    err.response = res
    raise err

