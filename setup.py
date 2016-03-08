#!/usr/bin/env python

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

install_requires = [
    'requests>=2.7.0',
    'xmltodict>=0.9.2',
]

setup(
    name='pinkopy',
    version='1.3.dev',
    description='Python wrapper for Commvault api',
    long_description=readme,
    author='Herkermer Sherwood',
    author_email='theherk@gmail.com',
    url='https://github.com/theherk/pinkopy',
    download_url='https://github.com/theherk/pinkopy/archive/1.3.dev.zip',
    packages=find_packages(),
    platforms=['all'],
    license='MIT',
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: Other/Proprietary License',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Utilities',
    ],
)
