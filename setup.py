#!/usr/bin/python -tt

import os
from distutils.core import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

VERSION='0.3'
NAME='howler'

setup(
    version=VERSION,
    url='https://github.com/mricon/howler',
    name=NAME,
    description='Alert when users log in from new locations',
    author='Konstantin Ryabitsev',
    author_email='mricon@kernel.org',
    packages=[NAME],
    license='GPLv3+',
    long_description=read('README.rst'),
)
