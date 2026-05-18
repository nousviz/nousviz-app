from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="HealthLogRow")


@_attrs_define
class HealthLogRow:
    """A single health_log entry — a snapshot of a periodic check.

    Attributes:
        id (int):
        level (str): 'healthy' | 'warning' | 'error'.
        checks (Any | Unset): JSONB array of check-result dicts (id, status, label, detail).
        postgres_ok (bool | None | Unset):
        tables (int | None | Unset):
        version (None | str | Unset):
        created_at (None | str | Unset):
    """

    id: int
    level: str
    checks: Any | Unset = UNSET
    postgres_ok: bool | None | Unset = UNSET
    tables: int | None | Unset = UNSET
    version: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        level = self.level

        checks = self.checks

        postgres_ok: bool | None | Unset
        if isinstance(self.postgres_ok, Unset):
            postgres_ok = UNSET
        else:
            postgres_ok = self.postgres_ok

        tables: int | None | Unset
        if isinstance(self.tables, Unset):
            tables = UNSET
        else:
            tables = self.tables

        version: None | str | Unset
        if isinstance(self.version, Unset):
            version = UNSET
        else:
            version = self.version

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "level": level,
            }
        )
        if checks is not UNSET:
            field_dict["checks"] = checks
        if postgres_ok is not UNSET:
            field_dict["postgres_ok"] = postgres_ok
        if tables is not UNSET:
            field_dict["tables"] = tables
        if version is not UNSET:
            field_dict["version"] = version
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        level = d.pop("level")

        checks = d.pop("checks", UNSET)

        def _parse_postgres_ok(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        postgres_ok = _parse_postgres_ok(d.pop("postgres_ok", UNSET))

        def _parse_tables(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        tables = _parse_tables(d.pop("tables", UNSET))

        def _parse_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        version = _parse_version(d.pop("version", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        health_log_row = cls(
            id=id,
            level=level,
            checks=checks,
            postgres_ok=postgres_ok,
            tables=tables,
            version=version,
            created_at=created_at,
        )

        health_log_row.additional_properties = d
        return health_log_row

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
