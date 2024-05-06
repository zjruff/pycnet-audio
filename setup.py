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
    install_requires = [
        "numpy==1.23",
        "tensorflow-cpu==2.2",
        "protobuf==3.20",
        "pillow==8.2",
        "pandas==1.4"
    ],
    entry_points = {
        "console_scripts": [
            "inventory_folder = pycnet.process.MakeFileInventory:main",
            "generate_spectrograms = pycnet.process.GenerateSpectrograms:main",
            "generate_class_scores = pycnet.process.GenerateClassScores:main",
            "process_folder = pycnet.process.ProcessFolder:main",
            "pycnet = pycnet.__main__:main",
            "test_pycnet = pycnet.process.TestPycnet:main"
        ],
    },
    packages=setuptools.find_packages(),
    package_data={
        'pycnet.cnet': [
            "PNW-Cnet_v4_TF.h5",
            "PNW-Cnet_v5_TF.h5",
            "target_classes.csv"
        ]
    },
    include_package_data=True
)

