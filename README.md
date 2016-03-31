pinkopy
=======

[![Join the chat at https://gitter.im/theherk/pinkopy](https://badges.gitter.im/theherk/pinkopy.svg)](https://gitter.im/theherk/pinkopy?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[![Build Status](https://travis-ci.org/theherk/pinkopy.svg)](https://travis-ci.org/theherk/pinkopy)
[![PyPI Version](https://img.shields.io/pypi/v/pinkopy.svg)](https://pypi.python.org/pypi/pinkopy)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pinkopy.svg)](https://pypi.python.org/pypi/pinkopy)

pinkopy is a Python wrapper for the Commvault api. Support for Commvault v11 api was added in v2.0.0.

Installation
------------

### from PyPI

    pip install pinkopy

### from source

    git clone git@github.com:theherk/pinkopy.git
    pip install pinkopy

Usage
-----

```python
from pinkopy import CommvaultSession

config = {
    'service': 'service url',
    'user': 'username',
    'pw': 'password'
}

with CommvaultSession(**config) as commvault:
    client_jobs = commvault.jobs.get_jobs('1234', job_filter="Backup")
    cust_jobs = commvault.jobs.get_subclient_jobs(client_jobs, '12345678', last=3)
    # multi status
    for job in cust_jobs:
        job_id = job['jobSummary']['jobId']
        job_details = commvault.jobs.get_job_details('1234', job_id)
        job_vmstatus = commvault.jobs.get_job_vmstatus(job_details)
```

pinkopy doesn't have to be used as a context manager.

```python
commvault = CommvaultSession(**config)
```

pinkopy used to have all the methods on one class. Now, the methods are divided among several classes and are similar to how the api, itself, is laid out. However, the methods that existed when the modularity was introduced, a shim was also introduced to be backwards compatible. So those methods can be called on the CommvaultSession instance directly.

```python
client_properties = commvault.clients.get_client_properties('2234')
# or the old way
client_properties = commvault.get_client_properties('2234')
```

This way, you old code works. In addition, you can instantiate just the session you need if you prefer.

```python
with SubclientSession(**config) as subclients:
    subclients = subclients.get_subclients('2234')
```

### Cache

The biggest introduction in 2.0.0 was an improved take on caching. Rather than implementing our own ill-conceived cache, we implemented a great [ttl_cache](https://pythonhosted.org/cachetools/#cachetools.func.ttl_cache) that uses [lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache) from the core library. It is from a library called [cachetools](https://pythonhosted.org/cachetools/). The implementation allows you to pass in a list of methods you want to use this cache or provides very sensible defaults if you don't.

The cache, for the duration of `cache_ttl`, will respond with the previous return value without running the function. So, for instance, the `get_clients` call could take several seconds on the first call, but only a few milliseconds on following calls.

By default, we cache for 20 minutes, but you can set this value, too.

```python
cache_methods = ['get_clients', 'get_subclients']
with CommvaultSession(cache_ttl=120, cache_methods=cache_methods, **config) as commvault:
    clients1 = commvault.clients.get_clients() # slow
    clients2 = commvault.clients.get_clients() # fast
    # ... fast
```

Or turn off the cache entirely.

```python
with CommvaultSession(use_cache=False, **config) as commvault:
    clients1 = commvault.clients.get_clients() # slow
    clients2 = commvault.clients.get_clients() # slow but fresh
```

Contribution
------------

Please do contribute to this repository. It currently only supports a small set of the api provided by Commvault. However, if you do contribute, please follow these guidelines.

### Guidelines

+ Use [Gitflow](https://www.atlassian.com/git/tutorials/comparing-workflows/). Your pull requests must come from a Gitflow branch.
    - feature/yourfeature
    - bugfix/issuenumber
+ **ONLY** imperative commit messages. Line one is one imperative, brief sentence. Following lines may have more details.
+ Builds must pass (which should be pretty easy right now, since there are no tests).
+ Never commit binary files.
+ Make sure you are committing with your Github user.

---

#### Name

The name was originally going to be commpy, but then I liked commiepy. From here it was only a small leap to pinkopy, a tribute to a dear friend of mine.

<img src="http://i.imgur.com/gAs94pn.png" alt="Pinkie Pie" width="200">
