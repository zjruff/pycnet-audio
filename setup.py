import setuptools

with open("README.md") as readme:
    long_description = readme.read()

setuptools.setup(
	name="pycnet",
	version="0.0.1",
    author="Zack Ruff",
    author_email="zjruff@gmail.com",
    description="Audio processing with PNW-Cnet",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages()
)