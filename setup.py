from setuptools import setup, find_packages

setup(
    name='CatWeazle',
    version='0.0.17',
    description='CatWeazle, dynamic DNS and Redhat IdM/FreeIPA registration system',
    long_description="""
dynamically create and delete DNS records for volatile linux systems, as well as redhat IDM de/registration.

Copyright (c) 2019, Stephan Schultchen.

License: MIT (see LICENSE for details)
    """,
    packages=find_packages(),
    scripts=[
        'contrib/catweazle',
        'contrib/catweazle_register',
    ],
    url='https://github.com/schlitzered/CatWeazle',
    license='MIT',
    author='schlitzer',
    author_email='stephan.schultchen@gmail.com',
    include_package_data=True,
    test_suite='test',
    platforms='posix',
    classifiers=[
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3'
    ],
    install_requires=[
        "aioboto3",
        "aiohttp",
        "aiotask-context",
        "aiohttp-remotes",
        "ipaddress",
        "jsonschema",
        "motor",
        "pyyaml",
        "passlib",
        "requests",
        "aioredis",
    ],
    keywords=[
        'freeipa', 'redhat idm', 'dns'
    ]
)
