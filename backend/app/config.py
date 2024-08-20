#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app.utils import PathUtil


MAIN_KEY = 'f0d8f7aa828d60106968a6067ea19dbfa0d2d2e067eda19dbfa0d2d2e235d37e5198842dca67ea'
DB_PASS = '123456'
ROOT_NAME = 'easy_fastapi'


class Setting(object):
    # 数据库链接路径
    DB_URI = f'mysql://root:{DB_PASS}@127.0.0.1:3306/easy_fastapi'
    # Upload 文件夹
    UPLOAD_FOLDER   = PathUtil.getProjectRoot(ROOT_NAME, 'upload')
    # 模板文件夹
    TEMPLATE_FOLDER = PathUtil.getProjectRoot(ROOT_NAME, 'frontend/dist')
    # 静态资源文件夹
    STATIC_FOLDER   = PathUtil.getProjectRoot(ROOT_NAME, 'frontend/dist/static')
    # 允许的图片上传格式
    ALLOWED_IMAGE_EXTENSIONS = set(['jpg', 'png', 'webp', 'gif'])
