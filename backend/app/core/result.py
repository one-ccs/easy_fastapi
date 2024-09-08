#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel


class JSONResponseResult(object):
    """返回 JSONResponse"""

    def __new__(
        cls,
        message: str = '请求成功',
        *,
        data: Any | None = None,
        code: int = 200,
        schema: BaseModel | None = None
    ) -> JSONResponse:
        """规范化响应数据。
        返回 JSONResponse 时，路由装饰器的 response_model 参数将无效，需手动
        指定 schema 进行序列化。

        Args:
            message (str, optional): 响应消息.
            data (Any, optional): 响应数据.
            code (int, optional): 响应状态码.
            schema (BaseModel, optional): 响应数据 schema.

        Returns:
            JSONResponse: JSONResponse 对象.
        """
        data = jsonable_encoder(data)

        if schema:
            data = jsonable_encoder(schema(**data))

        return JSONResponse(
            {'code': code, 'message': message, 'data': data},
            status_code=code,
        )

    @classmethod
    def failure(cls, message: str = '请求失败', *, data: Any | None = None, schema: BaseModel | None = None) -> JSONResponse:
        return cls(message, data=data, code=400, schema=schema)

    @classmethod
    def unauthorized(cls, message: str = '请登录后操作') -> JSONResponse:
        return cls(message, data=None, code=401)

    @classmethod
    def forbidden(cls, message: str = '您无权进行此操作') -> JSONResponse:
        return cls(message, data=None, code=403)

    @classmethod
    def error_404(cls, message: str = '什么都没有') -> JSONResponse:
        return cls(message, data=None, code=404)

    @classmethod
    def method_not_allowed(cls, message: str = '不允许的请求方法') -> JSONResponse:
        return cls(message, data=None, code=405)


class Result(object):
    """返回 dict"""

    def __new__(cls, message: str = '请求成功', *, data: Any | None = None, code: int = 200) -> dict:
        return {'code': code, 'message': message, 'data': data}

    @classmethod
    def failure(cls, message: str = '请求失败', *, data: Any | None = None) -> dict:
        return cls(message, data=data, code=400)

    @classmethod
    def unauthorized(cls, message: str = '请登录后操作') -> dict:
        return cls(message, data=None, code=401)

    @classmethod
    def forbidden(cls, message: str = '您无权进行此操作') -> dict:
        return cls(message, data=None, code=403)

    @classmethod
    def error_404(cls, message: str = '什么都没有') -> dict:
        return cls(message, data=None, code=404)

    @classmethod
    def method_not_allowed(cls, message: str = '不允许的请求方法') -> dict:
        return cls(message, data=None, code=405)

    @staticmethod
    def of(data_type: Any, *, class_name: str | None = None) -> BaseModel:
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
