from setuptools import setup, find_packages

setup(
    name="ai-cli",
    version="3.0.0",
    packages=find_packages(),
    py_modules=["aicli"],
    install_requires=[
        "groq",
        "questionary",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "ai-cli=aicli:main",
        ],
    },
    author="Anay Rustogi",
    description="A Terminal AI Agent running on Groq",
    long_description=open("README.md").read() if open("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/Anay-Rustogi/ai-cli",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
