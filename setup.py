# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


setup(
    name="imio.pm.wsclient",
    version="3.0.0.dev0",
    description="WebServices Client for PloneMeeting",
    long_description=open("README.txt").read() + "\n\n" + open("CHANGES.rst").read(),
    # Get more strings from
    # http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Framework :: Plone",
        "Framework :: Plone :: 6.2",
        "Framework :: Plone :: Addon",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    keywords="",
    author="Gauthier Bastien",
    author_email="devs@imio.be",
    url="https://github.com/IMIO/imio.pm.wsclient",
    license="GPL",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    python_requires=">=3.10",
    install_requires=[
        "setuptools",
        "collective.z3cform.datagridfield",
        "imio.pm.locales",
        "natsort",
        "plone.api",
        "plone.app.contenttypes",
        "plone.memoize",
        "requests",
    ],
    extras_require={"test": ["plone.app.testing", "plone.app.robotframework"]},
    entry_points="""
    # -*- Entry points: -*-
    """,
)
