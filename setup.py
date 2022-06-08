from setuptools import setup, find_packages

setup(
    name='django-cache-helper',
    version='1.0.0',
    description='Helps cache stuff',
    author='YCharts',
    author_email='operator@ycharts.com',
    url='https://github.com/ycharts/django_cache_helper.git',
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
