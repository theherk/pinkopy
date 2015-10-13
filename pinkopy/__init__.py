"""
pinkopy is a Python wrapper for the Commvault API
"""

__title__ = 'pinkopy'
__author__ = 'Herkermer Sherwood'

# bring the session handler into package namespace
from .commvault import CommvaultSession

# only provide session handler in *
__all__ = ['CommvaultSession']

# Set default logging handler to avoid "No handler found" warnings.
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
