#!/usr/bin/python3

from setuptools import setup

data_files = [('/usr/local/etc', ['dockerfile_generator.cfg'])]


setup(
    name='dockerfile_generator',
    description='Methoden zum erstellen von Docker Images',
    long_description = """Diese Modul enthaelt Methoden um ein Image aus Docker Hup zu
    modifiziren. Dabei koennen Sorces von Git, HTTP und localen System eingetragen werden
    und das Dockerfile modifizirt und erweitert werden. Images werden so erstellt das die
    vorherige Version unter den Tag old abgelegt werden. Methoden um Images zu testet und
    in eine Registry hochzuladen sind ebenfals intigriert.""",
    author='Juergen Ofner',
    version='0.30',
    py_modules=['dockerfile_generator'],
    data_files=data_files,
    install_requires=['docker==2.7.0', 'tqdm'],
    classifiers = [
        'Programming Language :: Python :: 3',
        'Development Status :: 5 - Production/Stable',
    ]
)
