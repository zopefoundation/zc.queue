from setuptools import setup

tests_require = ["zope.testing"]

setup(
    name="zc.queue",
    version="1.2dev",
    license="ZPL 2.1",
    author="Zope Project",
    author_email="zope3-dev@zope.org",

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
        test=tests_require),
    description=open('README.txt').read(),
    long_description=(
        open("CHANGES.txt").read() + "\n\n" +
        open("src/zc/queue/queue.txt").read()),
    keywords="zope zope3",
    zip_safe=False
    )