#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


with open('readme.md', 'r', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()


setup(
    name='easy_fastapi',
    version='0.13.1',
    description='基于 FastAPI 开发的后端框架，集成了 Tortoise ORM、Pydantic、Aerich、PyJWT、PyYAML、Redis 等插件，并且可以在编写好 `models` 文件后执行 `manager.py gen` 命令，批量生成 `schemas`、`routers`、`services` 代码，旨在提供一个高效、易用的后端开发环境。该框架通过清晰的目录结构和模块化设计，大大减少了项目的前期开发工作，帮助开发者快速构建和部署后端服务。',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='one-ccs',
    author_email='one-ccs@foxmal.com',
    url='https://github.com/one-ccs/easy_fastapi',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3.10',
    packages=find_packages(),
    package_dir={},
    package_data={
        'easy_fastapi': [
            'templates/**',
            'templates/.gitignore',
        ],
    },
    include_package_data=False,
    exclude_package_data={
        '': [
            '**/__pycache__/**',
        ],
    },
    install_requires=[
        'easy_pyoc>=0.9.1',
        'fastapi>=0.115.4',
        'tortoise-orm>=0.21.7',
        'pydantic>=2.10.6',
        'aerich>=0.7.2',
        'pyjwt>=2.9.0',
        'pyyaml>=6.0.2',
        'redis>=5.2.0',
        'bcrypt>=4.2.0',
    ],
    extras_require={},
    entry_points={
        'console_scripts': [
            'easy_fastapi = easy_fastapi.management:execute_from_command_line',
        ],
    },
)
