from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PostgresSummary")


@_attrs_define
class PostgresSummary:
    """
    Attributes:
        db_size_mb (int):
        cache_hit_pct (float): 0-100; target > 99 on a healthy install
        active_connections (int):
        idle_connections (int):
        max_connections (int):
        pg_stat_statements_installed (bool):
    """

    db_size_mb: int
    cache_hit_pct: float
    active_connections: int
    idle_connections: int
    max_connections: int
    pg_stat_statements_installed: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        db_size_mb = self.db_size_mb

        cache_hit_pct = self.cache_hit_pct

        active_connections = self.active_connections

        idle_connections = self.idle_connections

        max_connections = self.max_connections

        pg_stat_statements_installed = self.pg_stat_statements_installed

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "db_size_mb": db_size_mb,
                "cache_hit_pct": cache_hit_pct,
                "active_connections": active_connections,
                "idle_connections": idle_connections,
                "max_connections": max_connections,
                "pg_stat_statements_installed": pg_stat_statements_installed,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        db_size_mb = d.pop("db_size_mb")

        cache_hit_pct = d.pop("cache_hit_pct")

        active_connections = d.pop("active_connections")

        idle_connections = d.pop("idle_connections")

        max_connections = d.pop("max_connections")

        pg_stat_statements_installed = d.pop("pg_stat_statements_installed")

        postgres_summary = cls(
            db_size_mb=db_size_mb,
            cache_hit_pct=cache_hit_pct,
            active_connections=active_connections,
            idle_connections=idle_connections,
            max_connections=max_connections,
            pg_stat_statements_installed=pg_stat_statements_installed,
        )

        postgres_summary.additional_properties = d
        return postgres_summary

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
