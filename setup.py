import os

from setuptools import setup


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


tests_require = ["zope.testing"]


setup(
    name="zc.queue",
    version="1.4dev",
    license="ZPL 2.1",
    author="Zope Project",
    author_email="zope-dev@zope.org",
    # Get more strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        ],
    namespace_packages=["zc"],
    packages=["zc", "zc.queue"],
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "setuptools",
        "ZODB3",
        "zope.interface",
    ],
    tests_require=tests_require,
    extras_require=dict(
        test=tests_require,
        ),
    description=read('README.txt'),
    long_description='\n\n'.join([
        read('src', 'zc', 'queue', 'queue.txt'),
        read('CHANGES.txt'),
        ]),
    keywords="zope zope3",
    zip_safe=False
    )
