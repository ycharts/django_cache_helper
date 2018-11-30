from setuptools import setup, find_packages

setup(
    name='django-cache-helper',
    version="0.1",
    description='Helps cache stuff',
    author='James Bianco',
    author_email='jsbianco33@gmail.com',
    url='https://github.com/jb076/django_cache_helper.git',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['setuptools'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
