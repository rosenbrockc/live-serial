#!/usr/bin/env python
try:
    from setuptools import setup
    args = {}
except ImportError:
    from distutils.core import setup
    print("""\
*** WARNING: setuptools is not found.  Using distutils...
""")

from setuptools import setup
try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

from os import path
setup(name='live-serial',
      version='0.0.2',
      description='Real-time serial port plotter/logger.',
      long_description= "" if not path.isfile("README.md") else read_md('README.md'),
      author='Conrad W Rosenbrock',
      author_email='rosenbrockc@gmail.com',
      url='https://github.com/rosenbrockc/live-serial',
      license='MIT',
      setup_requires=['pytest-runner',],
      tests_require=['pytest', 'python-coveralls'],
      install_requires=[
          "argparse",
          "termcolor",
          "pytest",
          "python-coveralls",
          "numpy",
          "matplotlib",
          "pyserial",
      ],
      packages=['liveserial'],
      scripts=['liveserial/livemon.py'],
      package_data={'liveserial': []},
      include_package_data=True,
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Science/Research',
          'Natural Language :: English',
          'Operating System :: MacOS',
          'Operating System :: Microsoft :: Windows',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.5',
      ],
     )
