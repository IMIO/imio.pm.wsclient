from setuptools import setup, find_packages
import os

version = '1.9'

setup(name='imio.pm.wsclient',
      version=version,
      description="WebServices Client for PloneMeeting",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Plone",
        ],
      keywords='',
      author='',
      author_email='',
      url='http://svn.communesplone.org/svn/communesplone/imio.pm.wsclient/',
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
          # -*- Extra requirements: -*-
          'suds-jurko',
      ],
      extras_require={'test': ['plone.app.testing', 'unittest2', 'imio.pm.ws']},
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
