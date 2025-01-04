from setuptools import setup, find_packages
REQUIREMENTS = [i.strip() for i in open("requirements.txt").readlines()]

setup(
    name="armory-http",
    version="1.0.0",
    description="A simple HTTP server with progress bar and upload function.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Sandro",
    url="https://github.com/exgaso/armory-http",
    packages=find_packages(),
    install_requires=[REQUIREMENTS],
    entry_points={
        "console_scripts": [
            "armory-http=app.server:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
