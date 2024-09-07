#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from .config import FORCE_200_CODE


class JSONResponseResult(object):
    """返回 JSONResponse"""

    # 是否强制响应 200 状态码
    force_200_code = FORCE_200_CODE

    def __new__(cls, *, code: int, message: str, data: Any, schema: BaseModel) -> JSONResponse:
        """规范化响应数据。
        若 force_200_code = True，强制除 500 外的状态码为 200。此时返回
        JSONResponse 并使路由装饰器的 response_model 参数无效，需手动指定
        schema 进行序列化。

        Args:
            code (int, optional): 响应状态码.
            message (str, optional): 响应消息.
            data (Any, optional): 响应数据.
            schema (BaseModel, optional): 响应数据 schema.

        Returns:
            JSONResponse: JSONResponse 对象.
        """
        data = jsonable_encoder(data)

        if schema:
            data = jsonable_encoder(schema(**data))

        return JSONResponse(
            {'code': code, 'message': message, 'data': data},
            status_code=200 if cls.force_200_code else code,
        )

    @classmethod
    def success(cls, message = '请求成功', /, *, data=None, schema: BaseModel | None = None):
        return cls(message=message, data=data, code=200, schema=schema)

    @classmethod
    def failure(cls, message = '请求失败', /, *, data=None, schema: BaseModel | None = None):
        return cls(message=message, data=data, code=400, schema=schema)

    @classmethod
    def unauthorized(cls, message = '请登录后操作', /):
        return cls(message=message, data=None, code=401, schema=None)

    @classmethod
    def forbidden(cls, message = '您无权进行此操作', /):
        return cls(message=message, data=None, code=403, schema=None)

    @classmethod
    def error_404(cls, message = '什么都没有', /):
        return cls(message=message, data=None, code=404, schema=None)

    @classmethod
    def method_not_allowed(cls, message = '不允许的请求方法', /):
        return cls(message=message, data=None, code=405, schema=None)


class Result():
    """返回 dict"""

    def __new__(cls, message: str = '请求成功', /, *, data: Any = None) -> dict:
        return {'code': 200, 'message': message, 'data': data}


def result_of(data_type: Any, *, class_name: str | None = None) -> BaseModel:
    """返回结构化的 BaseModel 类

    Args:
        data_type (Any | None, optional): data 的数据类型. Defaults to None.
        class_name (str, optional): 类型名称. Defaults to 'Result'.

    Returns:
        BaseModel: 结构化的 BaseModel 类.
    """
    if data_type.__class__ is type and not class_name:
        raise ValueError('若 data_type 不是 BaseModel 类，则必须指定 class_name 参数')

    if data_type is None:
        name = 'Result'
    elif data_type.__class__ is type:
        name = f'Result{class_name}'
    else:
        name = f'Result{data_type.__name__}'

    bases = (BaseModel,)
    namespace = {
        '__annotations__': {
            'code': int,
            'message': str,
            'data': data_type,
        },
    }

    return type(name, bases, namespace)
