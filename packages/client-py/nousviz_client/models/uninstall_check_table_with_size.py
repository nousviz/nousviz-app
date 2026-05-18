from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="UninstallCheckTableWithSize")


@_attrs_define
class UninstallCheckTableWithSize:
    """B280 (v0.9.11.15): per-table data for the honest uninstall modal —
    name + current row count + size on disk. Drives the "exactly what will
    be dropped" disclosure block.

        Attributes:
            name (str):
            size_mb (float):
            rows (int):
    """

    name: str
    size_mb: float
    rows: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        size_mb = self.size_mb

        rows = self.rows

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "size_mb": size_mb,
                "rows": rows,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        size_mb = d.pop("size_mb")

        rows = d.pop("rows")

        uninstall_check_table_with_size = cls(
            name=name,
            size_mb=size_mb,
            rows=rows,
        )

        uninstall_check_table_with_size.additional_properties = d
        return uninstall_check_table_with_size

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
