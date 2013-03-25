try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


version = __import__('wayly_fabric').__version__

setup(
    name='wayly_fabric',
    version=version,
    packages=['wayly_fabric'],
    url='https://github.com/waylybaye/fabirc',
    license='MIT',
    author='waylybaye',
    author_email='waylybaye@wayly.net',
    description='A resuable django deploy fabfile',
    install_requires=['fabric>=1.6.0'],
)
