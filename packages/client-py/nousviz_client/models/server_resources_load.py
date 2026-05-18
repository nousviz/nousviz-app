from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ServerResourcesLoad")


@_attrs_define
class ServerResourcesLoad:
    """
    Attributes:
        load_1m (float):
        load_5m (float):
        load_15m (float):
    """

    load_1m: float
    load_5m: float
    load_15m: float
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        load_1m = self.load_1m

        load_5m = self.load_5m

        load_15m = self.load_15m

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "load_1m": load_1m,
                "load_5m": load_5m,
                "load_15m": load_15m,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        load_1m = d.pop("load_1m")

        load_5m = d.pop("load_5m")

        load_15m = d.pop("load_15m")

        server_resources_load = cls(
            load_1m=load_1m,
            load_5m=load_5m,
            load_15m=load_15m,
        )

        server_resources_load.additional_properties = d
        return server_resources_load

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
