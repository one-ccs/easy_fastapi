#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os import path
from pathlib import Path


class PathUtil(object):

    @staticmethod
    def get_project_root(root_name: str, join_path: str | None = None) -> str:
        """ 返回项目根目录的绝对地址

        :param root_name 跟文件夹名称
        :param join_path 拼接路径
        """
        root_path = __file__[:__file__.index(root_name) + len(root_name)]

        if join_path:
            return str(Path(root_path).joinpath(join_path))
        return root_path

    @staticmethod
    def abspath(_path: str = '') -> str:
        """ 返回路径的绝对路径 """
        return path.abspath(_path)

    @staticmethod
    def is_exists_file(_path: str) -> bool:
        """ 判断文件是否存在 """
        return path.exists(_path) and path.isfile(_path)

    @staticmethod
    def is_exists_dir(_path: str) -> bool:
        """ 判断路径是否是个存在 """
        return path.exists(_path) and path.isdir(_path)
