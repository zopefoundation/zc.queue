from setuptools import setup

setup(
    name="zc.queue",
    version="1.0",
    license="ZPL 2.1",
    author="Gary Poster",
    author_email="gary@zope.com",

    namespace_packages=["zc"],
    packages=["zc", "zc.queue"],
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=["zope.interface", "ZODB3"],
    tests_require=["zope.testing"],
    )
