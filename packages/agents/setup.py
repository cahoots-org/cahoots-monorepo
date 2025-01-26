from setuptools import setup, find_namespace_packages

setup(
    name="cahoots-agents",
    version="0.1.0",
    description="AI agents for Cahoots",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "cahoots-core>=0.1.0",
        "openai>=1.0.0",
        "anthropic>=0.3.0",
        "pytest>=7.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.1.0",
        "pytest-mock>=3.11.1",
        "pytest-randomly>=3.15.0",
        "pytest-timeout>=2.1.0",
        "pytest-xdist>=3.3.1",
    ],
    extras_require={
        "test": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.1",
            "pytest-randomly>=3.15.0",
            "pytest-timeout>=2.1.0",
            "pytest-xdist>=3.3.1",
        ]
    }
) 