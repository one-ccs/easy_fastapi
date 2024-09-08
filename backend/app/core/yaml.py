#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
