import setuptools

with open("readme.md", "r") as f:
    long_description = f.read()


setuptools.setup(
    name = "pet-feeder-api",
    version = "0.2.0",
    author = "CITS5506 Group 07",
    description = "API to interface with MongoDB",
    long_description = long_description,
    packages = ["feeder_api"],
    python_requires = ">=3.6",
    install_requires = [
        "pymongo",
        "bson",
        "bcrypt",
        "dnspython"
    ]
)
