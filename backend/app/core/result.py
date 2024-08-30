#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def json_encoder(func):
    def wrapper(*args, **kw):
        # 将 model 转为字典，若有 schema 则再转换一次
        if 'data' in kw:
            from app import models

            data = kw['data']
            if isinstance(data, models.Base):
                if 'schemas' in kw:
                    data = kw['schemas'](**vars(data))
                data = jsonable_encoder(data)
            kw['data'] = data

        return func(*args, **kw)
    return wrapper


class Result(object):

    # 为 True 返回真实的状态码，为 False 全部返回 200
    is_real_code = False


    def __new__(cls, value: bool, success_message='请求成功', failure_message='请求失败') -> JSONResponse:
        if value:
            return cls.success(success_message)
        else:
            return cls.failure(failure_message)

    @json_encoder
    @staticmethod
    def success(message='请求成功', data=None, code=200, schemas=None):
        return JSONResponse(
            {'code': code, 'message': message, 'data': data},
            code if Result.is_real_code else 200,
        )

    @json_encoder
    @staticmethod
    def failure(message='请求失败', data=None, code=400):
        return JSONResponse(
            {'code': code, 'message': message, 'data': data},
            code if Result.is_real_code else 200,
        )

    @staticmethod
    def unauthorized(message='请登录后操作'):
        return JSONResponse(
            {'code': 401, 'message': message, 'data': None},
            401 if Result.is_real_code else 200,
        )

    @staticmethod
    def forbidden(message='您无权进行此操作'):
        return JSONResponse(
            {'code': 403, 'message': message, 'data': None},
            403 if Result.is_real_code else 200,
        )

    @staticmethod
    def error_404(message='什么都没有'):
        return JSONResponse(
            {'code': 404, 'message': message, 'data': None},
            404 if Result.is_real_code else 200,
        )

    @staticmethod
    def method_not_allowed(message='不允许的请求方法'):
        return JSONResponse(
            {'code': 405, 'message': message, 'data': None},
            405 if Result.is_real_code else 200,
        )
