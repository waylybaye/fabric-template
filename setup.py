try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='wayly_fabric',
    version='0.0.1a',
    packages=['wayly_fabric'],
    url='https://github.com/waylybaye/deploy',
    license='MIT',
    author='waylybaye',
    author_email='waylybaye@wayly.net',
    description='A resuable django deploy fabfile'
)
