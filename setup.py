from setuptools import setup

setup(
    name="zc.queue",
    version="1.0",
    package_dir={"": "src"},

    install_requires=["zope.interface", "ZODB3"],
    tests_require=["zope.testing"],
    )
