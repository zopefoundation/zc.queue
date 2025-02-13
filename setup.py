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
import os

from setuptools import setup


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as f:
        return f.read()


setup(
    name="zc.queue",
    version='3.0.dev0',
    author="Zope Project",
    author_email="zope-dev@zope.dev",
    description=read('README.rst').splitlines()[0],
    long_description='\n\n'.join([
        read('src', 'zc', 'queue', 'queue.rst'),
        read('CHANGES.rst'),
    ]),
    keywords='zope zope3',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Framework :: Zope :: 3',
    ],
    url='https://github.com/zopefoundation/zc.queue',
    license="ZPL-2.1",
    namespace_packages=['zc'],
    packages=['zc', 'zc.queue'],
    package_dir={'': 'src'},
    include_package_data=True,
    python_requires='>=3.9',
    install_requires=[
        'setuptools',
        'ZODB',
        'persistent',
        'zope.interface',
    ],
    extras_require=dict(
        test=[
            "zope.testing",
            "zope.testrunner",
        ],
    ),
    zip_safe=False
)
