#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='piccata',
      version='2.0.1',
      description='Python CoAP Toolkit',
      author='Nordic Semiconductor',
      url='https://github.com/NordicSemiconductor/piccata',
      packages=find_packages(exclude=["*.test", "*.test.*"]),
     )
