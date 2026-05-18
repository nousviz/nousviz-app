from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="QueryRequest")


@_attrs_define
class QueryRequest:
    """
    Attributes:
        sql (str):
        database (None | str | Unset):
        db_engine (None | str | Unset):
        max_rows (int | None | Unset):
    """

    sql: str
    database: None | str | Unset = UNSET
    db_engine: None | str | Unset = UNSET
    max_rows: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        sql = self.sql

        database: None | str | Unset
        if isinstance(self.database, Unset):
            database = UNSET
        else:
            database = self.database

        db_engine: None | str | Unset
        if isinstance(self.db_engine, Unset):
            db_engine = UNSET
        else:
            db_engine = self.db_engine

        max_rows: int | None | Unset
        if isinstance(self.max_rows, Unset):
            max_rows = UNSET
        else:
            max_rows = self.max_rows

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "sql": sql,
            }
        )
        if database is not UNSET:
            field_dict["database"] = database
        if db_engine is not UNSET:
            field_dict["db_engine"] = db_engine
        if max_rows is not UNSET:
            field_dict["max_rows"] = max_rows

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sql = d.pop("sql")

        def _parse_database(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        database = _parse_database(d.pop("database", UNSET))

        def _parse_db_engine(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        db_engine = _parse_db_engine(d.pop("db_engine", UNSET))

        def _parse_max_rows(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        max_rows = _parse_max_rows(d.pop("max_rows", UNSET))

        query_request = cls(
            sql=sql,
            database=database,
            db_engine=db_engine,
            max_rows=max_rows,
        )

        query_request.additional_properties = d
        return query_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
