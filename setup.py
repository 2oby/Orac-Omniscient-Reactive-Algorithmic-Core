from setuptools import setup, find_packages

setup(
    name="orac",
    version="0.2.0-mvp",
    description="Omniscient Reactive Algorithmic Core - Ollama client optimized for Jetson",
    author="2oby",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "psutil>=5.9.0",  # For system monitoring
    ],
    entry_points={
        "console_scripts": [
            "orac=orac.cli:main_wrapper",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)