# coding=utf-8
from setuptools import find_packages, setup

setup(
    name="homura",
    packages=find_packages(),
    zip_safe=False,
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
)
