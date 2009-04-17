from setuptools import setup, find_packages
import sys, os

version = '0.2'

setup(name='MetaPython',
      version=version,
      description="Macro and code quoting facility for Python",
      long_description="""\
Basic macro and code quoting facility for Python.

Metapython includes an import hook that recognizes
".mpy" files as metapython files and performs macro
definition, expansion, and code instantiation at import-time.
""",
      classifiers=[
        # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Interpreters',
        ], 
      keywords='python, macro, code quoting, import hook',
      author='Rick Copeland',
      author_email='rick446@usa.net',
      url='http://metapython.org',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
