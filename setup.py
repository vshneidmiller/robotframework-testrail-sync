from setuptools import setup, find_packages

setup(
    name="robotframework-testrail-sync",
    version="0.0.25",
    description="A tool to synchronize Robot Framework tests with TestRail",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="Viacheslav Shneidmillier",
    author_email="v.shneidmiller@gmail.com",
    url="https://github.com/vshneidmiller/robotframework-testrail-sync",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "requests",
        "PyYAML",
        "robotframework"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'robotestrail=robotestrail.main:main',
        ],
    },
    python_requires='>=3.6',
)
