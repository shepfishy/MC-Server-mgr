from setuptools import setup, find_packages

setup(
    name="mc-server-manager",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PyQt5",
        "requests",
        "flask",
        "psutil",
    ],
)