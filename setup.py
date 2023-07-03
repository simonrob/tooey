import os

import setuptools

NAME = 'tooey'

about = {}
working_directory = os.path.join(os.path.abspath(os.path.dirname(__file__)), NAME)
with open(os.path.join(working_directory, '__version__.py')) as version_file:
    exec(version_file.read(), about)

with open('README.md') as readme_file:
    readme = readme_file.read()

# https://setuptools.pypa.io/en/latest/references/keywords.html or https://docs.python.org/3/distutils/apiref.html
setuptools.setup(
    name=NAME,
    version=about['__version__'],
    description=about['__description__'],
    long_description=readme,
    long_description_content_type='text/markdown',
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    project_urls={
        'Bug Tracker': '%s/issues' % about['__url__'],
        'Source Code': about['__url__'],
    },

    packages=[NAME],
    package_data={'': ['LICENSE']},
    include_package_data=True,

    license=about['__license__'],
    classifiers=about['__classifiers__']
)
