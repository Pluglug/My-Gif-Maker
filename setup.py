from setuptools import setup, find_packages

setup(
    name="gif_converter",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.9",
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "gif_converter=gif_converter.main:main",
        ],
    },
)
