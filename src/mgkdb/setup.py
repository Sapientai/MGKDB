from setuptools import setup, find_packages

setup(
    name="MGKDB",
    version="0.1.0",
    packages=find_packages(where="src"),
    install_requires=[ # dependencies
        'numpy==1.24.3', 
        'h5py', 'bson', 'pymongo'
    ],
    url="https://github.com/Sapientai/MGKDB",
    authors = [
    "Craig Michoski <michoski@gmail.com>",
    "Venkitesh Ayyar <venkiteshayyar@gmail.com>",
    "Dongyang Kuang <dykuangii@gmail.com>",
    "David Hatch <drdrhatch@googlemail.com>"
    ]
    description="Tools to acess MongoDB for nuclear fusion simulations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    # license="MIT",
    # classifiers=[
    #     "Programming Language :: Python :: 3",
    #     "License :: OSI Approved :: MIT License",
    #     "Operating System :: OS Independent",
    # ],
)