from setuptools import setup, find_packages

setup(
    name="robotframework-testrail-sync",
    version="0.0.1",
    description="A tool to synchronize Robot Framework tests with TestRail",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="Viacheslav Shneidmillier",
    author_email="v.shneidmiller@gmail.com",
    url="https://github.com/yourusername/robotestrail",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests",
        "PyYAML",
        "robotframework",
        "concurrent.futures"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'robotestrail=robotestrail.src.main:main',
        ],
    },
    python_requires='>=3.6',
)
