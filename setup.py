#!/usr/bin/env python

import os
import versioneer
from setuptools import setup


def parse_requirements(filename):
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

def get_requirements(filename):
    if not os.path.exists(filename):
        return []

    return parse_requirements(filename)

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

setup(name='django-xff',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Django X-Forwarded-For Properly',
      long_description=README,
      author='Ferrix Hovi',
      author_email='ferrix@codetry.fi',
      install_requires=get_requirements('requirements.txt'),
      packages=['xff'],
      url='https://github.com/ferrix/xff/',
      license='MIT License',
      classifiers=[
          'Environment :: Web Environment',
          'Framework :: Django',
          'Framework :: Django :: 1.8',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'License :: OSI Approved :: MIT License',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ],
      )
