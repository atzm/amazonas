#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


setup(
    name='amazonas',
    version='0.0.1',
    description='A sticky bot',
    author='Atzm WATANABE',
    author_email='atzm@atzm.org',
    license='BSD-2',
    entry_points={'console_scripts': [
        'amzcons = amazonas.amzcons:main',
        'amzweb  = amazonas.amzweb:main',
        'amzirc  = amazonas.amzirc:main',
        'amzmm   = amazonas.amzmm:main',
    ]},
    packages=find_packages(exclude=['test']),
    platforms=['Linux'],
    install_requires=[
        'flask>=0.10.1',
        'irc>=8.9.1,<=16.3',
        'lxml>=3.3.5',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
    ],
)
