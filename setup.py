#!/usr/bin/env python3
"""
Setup script for Edge Deployment Manager
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Edge Deployment Manager - A comprehensive edge deployment solution"

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    requirements = []
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return requirements

setup(
    name="edge-deployment-manager",
    version="1.0.0",
    description="A comprehensive edge deployment management system",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Olúmáyòwá Akinkuehinmi",
    author_email="akintunero101@gmail.com",
    url="https://github.com/akintunero/edge-deployment-manager",
    packages=find_packages(include=['src', 'src.*']),
    package_dir={'': '.'},
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'flake8>=5.0.0',
            'black>=22.0.0',
            'pre-commit>=2.20.0',
        ],
        'test': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'edge-manager=src.manager:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Internet :: WWW/HTTP",
    ],
    keywords="edge deployment docker kubernetes mqtt iot devops",
    project_urls={
        "Bug Reports": "https://github.com/akintunero/edge-deployment-manager/issues",
        "Source": "https://github.com/akintunero/edge-deployment-manager",
        "Documentation": "https://github.com/akintunero/edge-deployment-manager#readme",
    },
    include_package_data=True,
    zip_safe=False,
) 