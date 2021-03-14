#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages
from pkg_resources import parse_requirements

with open('README.rst') as readme_file:
    readme = readme_file.read()

history = ''

with open('requirements/prod.txt') as prod_req:
    requirements = [str(ir) for ir in parse_requirements(prod_req)]
with open('requirements/test.txt') as test_req:
    test_requirements = [str(ir) for ir in parse_requirements(test_req)]

setup(
    author="Lukas Lüftinger",
    author_email='lukas.lueftinger@outlook.com',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="PiCamera scripts",
    entry_points={
        'console_scripts': [
            'rpicam=rpicam.cli.main:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='rpicam',
    name='rpicam',
    packages=find_packages(include=['rpicam', 'rpicam.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/LokiLuciferase/rpicam',
    version='0.0.1',
    zip_safe=False,
)
