from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ServerResourcesDisk")


@_attrs_define
class ServerResourcesDisk:
    """
    Attributes:
        path (str):
        total_gb (float):
        used_gb (float):
        free_gb (float):
        used_pct (int):
    """

    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_pct: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        path = self.path

        total_gb = self.total_gb

        used_gb = self.used_gb

        free_gb = self.free_gb

        used_pct = self.used_pct

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "path": path,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "used_pct": used_pct,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        path = d.pop("path")

        total_gb = d.pop("total_gb")

        used_gb = d.pop("used_gb")

        free_gb = d.pop("free_gb")

        used_pct = d.pop("used_pct")

        server_resources_disk = cls(
            path=path,
            total_gb=total_gb,
            used_gb=used_gb,
            free_gb=free_gb,
            used_pct=used_pct,
        )

        server_resources_disk.additional_properties = d
        return server_resources_disk

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
