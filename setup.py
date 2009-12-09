from setuptools import setup, find_packages

version = '0.1.0'

LONG_DESCRIPTION = """
=====================================
Agilito
=====================================
"""

setup(
        name='agilito',
        version=version,
        description="agilito",
        long_description=LONG_DESCRIPTION,
        classifiers=[
            "Programming Language :: Python",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Framework :: Django",
            "Environment :: Web Environment",
            ],
        keywords='django,agile',
        author='',
        author_email='',
        url='http://www.ajellito.com',
        license='MIT',
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        setup_requires=['setuptools_git'],
        )
