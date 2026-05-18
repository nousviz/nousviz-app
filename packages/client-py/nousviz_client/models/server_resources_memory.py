from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ServerResourcesMemory")


@_attrs_define
class ServerResourcesMemory:
    """
    Attributes:
        total_mb (int):
        used_mb (int):
        free_mb (int):
        available_mb (int):
        buff_cache_mb (int):
    """

    total_mb: int
    used_mb: int
    free_mb: int
    available_mb: int
    buff_cache_mb: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        total_mb = self.total_mb

        used_mb = self.used_mb

        free_mb = self.free_mb

        available_mb = self.available_mb

        buff_cache_mb = self.buff_cache_mb

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "total_mb": total_mb,
                "used_mb": used_mb,
                "free_mb": free_mb,
                "available_mb": available_mb,
                "buff_cache_mb": buff_cache_mb,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        total_mb = d.pop("total_mb")

        used_mb = d.pop("used_mb")

        free_mb = d.pop("free_mb")

        available_mb = d.pop("available_mb")

        buff_cache_mb = d.pop("buff_cache_mb")

        server_resources_memory = cls(
            total_mb=total_mb,
            used_mb=used_mb,
            free_mb=free_mb,
            available_mb=available_mb,
            buff_cache_mb=buff_cache_mb,
        )

        server_resources_memory.additional_properties = d
        return server_resources_memory

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
