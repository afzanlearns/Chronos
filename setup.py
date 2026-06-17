from setuptools import setup, find_packages

setup(
    name="chronos",
    version="1.0.0",
    description="Chronos - App usage tracker and task manager",
    author="Chronos Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "flask>=3.0",
        "flask-cors>=4.0",
        "sqlalchemy>=2.0",
        "pygetwindow>=0.0.9",
        "plyer>=2.1",
        "apscheduler>=3.10",
        "python-dotenv>=1.0",
        "click>=8.1",
        "rich>=13.0",
        "pandas>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "chronos=chronos.cli.main:cli",
        ],
    },
)
