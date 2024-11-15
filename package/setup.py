#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


with open('../readme.md', 'r', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

setup(
    name='easy_fastapi',
    version='0.1.1',
    description='基于 FastAPI 开发的后端框架，集成了 Tortoise ORM、Pydantic、Aerich、PyJWT、PyYAML、Redis 等插件，并且可以在编写好 `models` 文件后执行 `manager.py gen` 命令，批量生成 `schemas`、`routers`、`services` 代码，旨在提供一个高效、易用的后端开发环境。该框架通过清晰的目录结构和模块化设计，大大减少了项目的前期开发工作，帮助开发者快速构建和部署后端服务。',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='one-ccs',
    author_email='one-ccs@foxmail.com',
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
    package_data={},
    exclude_package_data={},
    install_requires=[
        'easy_pyoc',
        'fastapi',
        'tortoise-orm',
        'pydantic',
        'aerich',
        'pyjwt',
        'pyyaml',
        'redis',
        'bcrypt',
    ],
    extras_require={},
    entry_points={
        'console_scripts': [
            'easy_fastapi = easy_fastapi.core.management:execute_from_command_line',
        ],
    },
)
