from setuptools import setup

setup(
    name="zc.queue",
    version="1.1",
    license="ZPL 2.1",
    author="Zope Project",
    author_email="zope3-dev@zope.org",

    namespace_packages=["zc"],
    packages=["zc", "zc.queue"],
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=["zope.interface", "ZODB3"],
    tests_require=["zope.testing"],
    description=open('README.txt').read(),
    long_description=(
        open("CHANGES.txt").read() + "\n\n" +
        open("src/zc/queue/queue.txt").read()),
    keywords="zope zope3",
    zip_safe=False
    )
