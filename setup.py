from setuptools import setup, find_packages

setup(
    name="ai-agents",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "swarm @ git+https://github.com/openai/swarm.git",
        "openai>=1.50.0",
    ],
    python_requires=">=3.12",
)
