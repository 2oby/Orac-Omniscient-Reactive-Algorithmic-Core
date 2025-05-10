from setuptools import setup, find_packages

setup(
    name="orac",
    version="0.2.0",
    packages=find_packages(),
    description="Omniscient Reactive Algorithmic Core - llama.cpp client optimized for Jetson",
    author="Toby",
    author_email="toby@example.com",
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.8.0",
        "httpx>=0.24.0",
        "python-dotenv>=0.19.0",
        "loguru>=0.5.3",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.18.0",
        "pytest-cov>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "orac=orac.cli:main",
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