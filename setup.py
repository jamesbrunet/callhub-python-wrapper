
from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(here, "callhub", "__version__.py"), mode="r") as f:
    exec(f.read(), about)

README = ""
with open(os.path.join(here, "README.md"), mode="r") as f:
    README = f.read()

tests_require = ["requests-mock"]
install_requires = ["requests==2.23.0", "ratelimit==2.2.1", "requests-futures==1.0.0"]

setup(
    name=about["__name__"],
    description=about["__description__"],
    long_description=README,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email=about["__authoremail__"],
    url=about["__url__"],
    version=about["__version__"],
    packages=["callhub"],
    install_requires=install_requires,
    tests_requre=tests_require,
    python_requires=">=3.5",
    keywords=["callhub", "api"],
    license=about["__license__"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Software Development",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)