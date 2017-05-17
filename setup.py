#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='piccata',
      version='1.0.0',
      description='Python CoAP Toolkit',
      author='Nordic Semiconductor',
      url='https://github.com/NordicSemiconductor/piccata',
      packages=find_packages(exclude=["*.test", "*.test.*"]),
      install_requires = ['ipaddress'],
     )
