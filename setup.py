from setuptools import setup, find_packages


def readme():
  with open('README.md', 'r') as f:
    return f.read()


setup(
  name='aiogram_dialog_manager',
  version='1.0.0',
  author='kuschanow',
  author_email='kuschanow@gmail.com',
  description='Dialog manager for aiogram.',
  long_description=readme(),
  long_description_content_type='text/markdown',
  url='https://github.com/RomanKuschanow',
  packages=find_packages(),
  install_requires=['aiogram>=3'],
  project_urls={
    'GitHub': 'https://github.com/RomanKuschanow/aiogram_dialog_manager'
  },
  python_requires='>=3.10'
)
