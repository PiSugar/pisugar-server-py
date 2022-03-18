from unicodedata import name
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pisugar",
    version="0.1.1",
    description="PiSugar server python api",
    author="PiSugar Team",
    author_email="app@pisugar.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PiSugar/pisugar-server-py",
    project_urls={
        "Official Website": "https://www.pisugar.com",
        "Bug Tracker": "https://github.com/PiSugar/pisugar-server-py/issues",
    },
    license="Apache License 2.0",
    keywords="PiSugar Raspberry Pi",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
)