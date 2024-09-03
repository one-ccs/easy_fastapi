#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime, timezone

import yaml


ENCODING  = 'utf-8'


def load_yaml(text: str) -> dict:
    """将 yaml 字符串转换为 dict"""
    return yaml.safe_load(text)


def dump_yaml(data: dict) -> str:
    """将 dict 转换为 yaml 字符串"""
    return yaml.safe_dump(data)


def read_yaml(yaml_file: str) -> dict:
    """读取 yaml 文件"""
    with open(yaml_file, 'r', encoding=ENCODING) as f:
        data = yaml.safe_load(f)
    return data


def write_yaml(data, yaml_file: str):
    """写入 yaml 文件"""
    with open(yaml_file, 'w', encoding=ENCODING) as f:
        yaml.safe_dump(data, f)


def read_yaml_config(config_path: str) -> dict:
    """读取程序配置文件，并替换内置变量

    Args:
        config_path (str): 配置文件路径

    Returns:
        dict: 配置字典
    """
    try:
        with open(config_path, 'r', encoding=ENCODING) as f:
            config = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f'配置文件 {config_path} 不存在')

    # 替换内置变量
    config = config.replace('${DATE}', datetime.now(timezone.utc).strftime(r'%Y-%m-%d'))
    config = config.replace('${TIME}', datetime.now(timezone.utc).strftime(r'%H:%M:%S'))

    return load_yaml(config)
