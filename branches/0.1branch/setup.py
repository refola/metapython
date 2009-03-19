from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='MetaPython',
      version=version,
      description="Macro and code quoting facility for Python",
      long_description="""\
Basic macro and code quoting facility for Python.
Jinja2 is used to expand code templates, allowing full
access to the Python language for generating code.

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
      url='http://code.google.com/p/metapython/',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
        'jinja2 >= 2.1.1'
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
