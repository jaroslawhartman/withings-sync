import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='withings-sync',
    version='3.3.0',
    author='Masayuki Hamasaki, Steffen Vogel',
    author_email='post@steffenvogel.de',
    description='A tool for synchronisation of Withings (ex. Nokia Health Body) to Garmin Connect and Trainer Road.',
    license='MIT',
    keywords='garmin withings sync api scale smarthome',
    url='http://packages.python.org/an_example_pypi_project',
    packages=['withings_sync'],
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        'lxml',
        'requests',
        'cloudscraper'
    ],
    entry_points={
        'console_scripts': [
            'withings-sync=withings_sync.sync:main'
        ],
    },
    zip_safe=False,
    include_package_data=True
)
