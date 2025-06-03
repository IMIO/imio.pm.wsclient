from setuptools import setup, find_packages
import os

version = '2.0.2'

setup(name='imio.pm.wsclient',
      version=version,
      description="WebServices Client for PloneMeeting",
      long_description=open("README.txt").read() + "\n\n" +
                       open(os.path.join("CHANGES.rst")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Framework :: Plone",
        "Framework :: Plone :: 4.3",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        ],
      keywords='',
      author='Gauthier Bastien',
      author_email='devs@imio.be',
      url='https://github.com/IMIO/imio.pm.wsclient',
      license='GPL',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['imio', 'imio.pm'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'collective.z3cform.datagridfield',
          'imio.pm.locales',
          'plone.memoize',
          'requests',
          'six',
      ],
      extras_require={'test': ['plone.app.testing', 'plonemeeting.restapi', 'mock']},
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
