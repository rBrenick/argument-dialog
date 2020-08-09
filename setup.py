from setuptools import setup, find_packages

setup(name='argument-dialog',
      version='0.1',
      description='argument-dialog',
      url='http://github.com/rBrenick/argument-dialog',
      author='Richard Brenick',
      author_email='RichardBrenick@gmail.com',
      license='MIT',
      zip_safe=False,

      install_requires=[
          "PySide2",
          "Qt.py"
      ],

      packages=find_packages(),

      package_data={'': ['*.*']},
      include_package_data=True,

      )
