from setuptools import setup, find_packages

setup(
    name="event_modeling_practice",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "behave>=1.2.6",
        "parse>=1.8.2",
        "parse-type>=0.4.2",
    ],
) 