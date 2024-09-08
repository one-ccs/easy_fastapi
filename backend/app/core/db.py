#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing_extensions import Self
from typing import Union, Optional, Sequence

from sqlalchemy.sql._typing import _JoinTargetArgument, _OnClauseArgument
from sqlmodel.sql.expression import SelectOfScalar, _ColumnExpressionArgument
from sqlmodel.orm.session import _TSelectParam
from sqlmodel import SQLModel, Session, create_engine, select
from pydantic import BaseModel, Field, PrivateAttr

from . import config


engine = create_engine(config.DATABASE_URI)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        BaseCRUD._session = session
        yield session
    BaseCRUD._session = None


class BaseCRUD(SQLModel):

    _session: Session = PrivateAttr(None)

    @classmethod
    def statement(cls) -> SelectOfScalar[_TSelectParam]:
        """返回当前的查询语句"""
        if cls._session._statement is None:
            raise Exception('CRUD Error: 请先调用 query 方法')
        return cls._session._statement

    @classmethod
    def query(cls, *whereclause: _ColumnExpressionArgument[bool] | bool) -> Union['BaseCRUD', Self]:
        """添加查询条件，并初始化查询语句"""
        if cls._session is None:
            raise Exception('CRUD Error: 请先调用 get_session 方法')
        cls._session._statement = select(cls).where(*whereclause)
        return cls

    @classmethod
    def join(cls,
        target: _JoinTargetArgument,
        onclause: Optional[_OnClauseArgument] = None,
        *,
        isouter: bool = False,
        full: bool = False,
    ) -> Union['BaseCRUD', Self]:
        """查询中添加 join 语句"""
        cls._session._statement = cls.statement().join(target, onclause, isouter=isouter, full=full)
        return cls

    @classmethod
    def count(cls) -> int:
        """返回查询结果的条数"""
        return cls._session.exec(cls.statement()).all().count()

    @classmethod
    def first(cls) -> Optional[Self]:
        """返回第一条查询结果"""
        return cls._session.exec(cls.statement()).first()

    @classmethod
    def all(cls) -> Sequence[Self]:
        """返回所有查询结果"""
        return cls._session.exec(cls.statement()).all()

    @classmethod
    def page(
        cls,
        page_index: int = Field(1, gt=0),
        page_size: int = Field(10, gt=0),
    ) -> dict[str, int | Sequence[Self] | bool]:
        """返回一页查询结果

        Args:
            page_index (int, optional): 页码（从 1 开始）. Defaults to Field(1, gt=0).
            page_size (int, optional): 每页条数. Defaults to Field(10, gt=0).

        Returns:
            dict[str, int | Sequence[Self] | bool]: 查询结果 {
                'total': 总条数,
                'items': 当前页结果,
                'finished': 是否是最后一页
            }
        """
        total = cls.count()
        offset = (page_index - 1) * page_size

        cls._session._statement = cls.statement().offset(offset).limit(page_size)

        return {
            'total': total,
            'items': cls.all(),
            'finished': total <= offset + page_size,
        }

    @classmethod
    def by_id(cls, id: int = Field(..., gt=0)) -> Optional[Self]:
        return cls.query(cls.id == id).first()

    @classmethod
    def delete(cls) -> Self:
        """删除当前查询语句的结果"""
        obj = cls.first()
        cls._session.delete(obj)
        cls._session.commit()
        return obj

    @classmethod
    def delete_all(cls) -> Sequence[Self]:
        """删除当前查询语句的所有结果"""
        objs = cls.all()
        for obj in objs:
            cls._session.delete(obj)
        cls._session.commit()
        return objs

    @classmethod
    def create(cls, source: dict | SQLModel | BaseModel) -> Self:
        """从 course 数据模型初始化一个对象"""
        return cls.model_validate(source)

    def save_or_update(self) -> Self:
        """插入或更新一条记录"""
        BaseCRUD._session.add(self)
        BaseCRUD._session.commit()
        BaseCRUD._session.refresh(self)

        return self
