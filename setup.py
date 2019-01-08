#!/usr/bin/env python

import os
import versioneer
from setuptools import setup
from pip.req import parse_requirements
from pip.download import PipSession


def get_requirements(filename):
    if not os.path.exists(filename):
        return []

    install_reqs = parse_requirements(filename, session=PipSession())
    return [str(ir.req) for ir in install_reqs]

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
