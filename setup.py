from setuptools import setup, find_packages

version = __import__('fabric_template').__version__

setup(
    name='fabric-template',
    version=version,
    packages=find_packages(),
    url='https://github.com/waylybaye/fabric-template',
    license='MIT',
    author='waylybaye',
    author_email='waylybaye@wayly.net',
    description='A reusable django deploy fabfile',
    install_requires=['fabric>=1.6.0'],
)
