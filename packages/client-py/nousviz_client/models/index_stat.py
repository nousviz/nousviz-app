from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="IndexStat")


@_attrs_define
class IndexStat:
    """
    Attributes:
        schema (str):
        table (str):
        name (str):
        size_mb (float):
        scans_lifetime (int):
        tuples_read (int):
        is_primary (bool | Unset): True for primary-key indexes. Surfaced so the unused_index diagnostic rule can
            exclude PKs (load-bearing for INSERT / UPDATE / DELETE + foreign-key lookups regardless of idx_scan count).
            Default: False.
        is_unique (bool | Unset): True for unique indexes (including PKs). Same exclusion rationale as is_primary —
            unique indexes enforce a constraint, not just speed up lookups. Default: False.
    """

    schema: str
    table: str
    name: str
    size_mb: float
    scans_lifetime: int
    tuples_read: int
    is_primary: bool | Unset = False
    is_unique: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        schema = self.schema

        table = self.table

        name = self.name

        size_mb = self.size_mb

        scans_lifetime = self.scans_lifetime

        tuples_read = self.tuples_read

        is_primary = self.is_primary

        is_unique = self.is_unique

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "schema": schema,
                "table": table,
                "name": name,
                "size_mb": size_mb,
                "scans_lifetime": scans_lifetime,
                "tuples_read": tuples_read,
            }
        )
        if is_primary is not UNSET:
            field_dict["is_primary"] = is_primary
        if is_unique is not UNSET:
            field_dict["is_unique"] = is_unique

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        schema = d.pop("schema")

        table = d.pop("table")

        name = d.pop("name")

        size_mb = d.pop("size_mb")

        scans_lifetime = d.pop("scans_lifetime")

        tuples_read = d.pop("tuples_read")

        is_primary = d.pop("is_primary", UNSET)

        is_unique = d.pop("is_unique", UNSET)

        index_stat = cls(
            schema=schema,
            table=table,
            name=name,
            size_mb=size_mb,
            scans_lifetime=scans_lifetime,
            tuples_read=tuples_read,
            is_primary=is_primary,
            is_unique=is_unique,
        )

        index_stat.additional_properties = d
        return index_stat

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
