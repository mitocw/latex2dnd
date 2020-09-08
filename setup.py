import glob
from setuptools import setup

def findfiles(pat):
    #return [x[10:] for x in glob.glob('latex2dnd/' + pat)]
    return [x for x in glob.glob('share/' + pat)]

data_files = [
    ('share/lib', findfiles('lib/*')),
    ('share/tex', findfiles('tex/*')),
    ('share/testtex', findfiles('testtex/*')),
    ]

# print "data_files = %s" % data_files

setup(
    name='latex2dnd',
    version='1.2.0',
    author='I. Chuang',
    author_email='ichuang@mit.edu',
    packages=['latex2dnd', 'latex2dnd.test'],
    scripts=[],
    url='http://pypi.python.org/pypi/latex2dnd/',
    license='LICENSE.txt',
    description='Generate edX drag-and-drop problems using compilation from latex',
    long_description=open('README.txt').read(),
    long_description_content_type='text/markdown',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'latex2dnd = latex2dnd.main:CommandLine',
            ],
        },
    install_requires=['lxml',
                      'path.py',
                      ],
    dependency_links = [
        ],
    package_dir={'latex2dnd': 'latex2dnd'},
    package_data={ 'latex2dnd': ['tex/*', 'testtex/*'] },
    # data_files = data_files,
    test_suite = "latex2dnd.test",
)

