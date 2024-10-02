#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing_extensions import Self
from typing import Type, Optional, Sequence
from abc import ABC

from sqlalchemy.sql._typing import _JoinTargetArgument, _OnClauseArgument
from sqlmodel.sql.expression import SelectOfScalar, _ColumnExpressionArgument
from sqlmodel.orm.session import _TSelectParam
from sqlmodel import SQLModel, Session, create_engine, select
from pydantic import BaseModel, Field

from . import config
from .exceptions import NotFoundException


engine = create_engine(config.DATABASE_URI)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


class SessionStatement(ABC):

    def __init__(self, cls, *whereclause: _ColumnExpressionArgument[bool] | bool):
        self.cls = cls
        self.session: Session = Session(engine)
        self.statement: SelectOfScalar[_TSelectParam] = select(cls).where(*whereclause)

    @classmethod
    def create(cls: Type[Self] | SQLModel, source: dict | SQLModel | BaseModel) -> Self:
        """从 course 数据模型初始化一个对象"""
        return cls.model_validate(source)

    @classmethod
    def by_id(cls, id: int = Field(..., gt=0)) -> Optional[Self]:
        """通过主键 id 查询对象

        Args:
            id (int, optional): 主键 id. Defaults to Field(..., gt=0).

        Returns:
            Self: 查询结果对象
        """
        return SessionStatement(cls, cls.id == id).first()

    @classmethod
    def query(cls, *whereclause: _ColumnExpressionArgument[bool] | bool) -> Self:
        """新建一个查询对象

        Args:
            *whereclause (_ColumnExpressionArgument[bool] | bool): 查询条件

        Returns:
            SessionStatement: 查询对象
        """
        return SessionStatement(cls, *whereclause)

    def join(self,
        target: _JoinTargetArgument,
        onclause: Optional[_OnClauseArgument] = None,
        *,
        isouter: bool = False,
        full: bool = False,
    ) -> Self:
        """多表查询

        Args:
            target (_JoinTargetArgument): 要加入的目标表
            onclause (Optional[_OnClauseArgument], optional): 连接条件. Defaults to None.
            isouter (bool, optional): 如果为 True，则使用 LEFT OUTER 连接. Defaults to False.
            full (bool, optional): 如果为 True，则使用 FULL OUTER 连接. Defaults to False.

        Returns:
            Self: 查询对象
        """
        self.statement = self.statement.join(target, onclause, isouter=isouter, full=full)
        return self

    def count(self) -> int:
        """返回查询结果的条数"""
        return len(self.session.exec(self.statement).all())

    def first(self) -> Optional[Self]:
        """返回第一条查询结果"""
        return self.session.exec(self.statement).first()

    def all(self) -> Sequence[Self]:
        """返回所有查询结果"""
        return self.session.exec(self.statement).all()

    def page(
        self,
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
        total = self.count()
        offset = (page_index - 1) * page_size

        self.statement = self.statement.offset(offset).limit(page_size)

        return {
            'total': total,
            'items': self.all(),
            'finished': total <= offset + page_size,
        }


    def delete(self) -> Self:
        """删除当前查询语句的结果

        Raises:
            NotFoundException: 删除失败，对象不存在

        Returns:
            Self: 删除的对象
        """
        obj = self.first()
        if obj is None:
            raise NotFoundException('删除失败，对象不存在')
        self.session.delete(obj)
        self.session.commit()
        return obj

    def delete_all(self) -> int:
        """删除当前查询语句的所有结果

        Returns:
            int: 删除数量
        """
        objs = self.all()
        for obj in objs:
            self.session.delete(obj)
        self.session.commit()
        return len(objs)

    def save_or_update(self) -> Self:
        """保存或更新当前对象

        Returns:
            Self: 更新后的当前对象
        """
        with Session(engine) as session:
            session.add(self)
            session.commit()
            session.refresh(self)
        return self
