##############################################################################
#
# Copyright (c) 2011 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Setup
"""
import os
from setuptools import setup

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

tests_require = ["zope.testing"]

setup(
    name="zc.queue",
    version='2.0.0a2.dev0',
    author="Zope Project",
    author_email="zope-dev@zope.org",
    description=read('README.txt'),
    long_description='\n\n'.join([
        read('src', 'zc', 'queue', 'queue.txt'),
        read('CHANGES.txt'),
        ]),
    keywords='zope zope3',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Framework :: Zope3'
        ],
    url='http://pypi.python.org/pypi/zc.queue',
    license="ZPL 2.1",
    namespace_packages=['zc'],
    packages=['zc', 'zc.queue'],
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'setuptools',
        'ZODB',
        'persistent',
        'zope.interface',
    ],
    tests_require=tests_require,
    test_suite='zc.queue.tests.test_suite',
    extras_require=dict(
        test=tests_require,
        ),
    zip_safe=False
    )
