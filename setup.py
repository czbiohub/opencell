#!/usr/bin/env python

import os
import setuptools

setuptools.setup(
    name='opencell',
    description='Opencell processing tools and backend',
    url='https://github.com/czbiohub/opencell',
    packages=setuptools.find_packages(),
    python_requires='>3.7',
    zip_safe=False,
)
