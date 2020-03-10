from sys import platform
from setuptools import setup, find_packages
from gdrove import __version__

with open("requirements.txt", "r") as f:
    install_requires = [o for o in [i.split("#")[0] for i in f.readlines()] if len(o) > 0]

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name="GDrove",
    version=__version__,
    packages=find_packages(),
    install_requires=install_requires,
    author="Spazzlo",
    description="A tool allowing you to copy, upload, and download GDrive folders.",
    url="https://github.com/Spazzlo/gdrove",
    include_package_data=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    entry_points={
        "console_scripts": [
            "gdrove = gdrove.run:main"
        ]
    }
)
