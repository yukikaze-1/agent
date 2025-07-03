# setup.py
from setuptools import setup, find_packages

setup(
    name="agent",
    version="0.1",
    packages=find_packages(),  # 自动收集 agent/ 下的所有包（包括 Service、Module、Tools 等）
    include_package_data=True,
)
