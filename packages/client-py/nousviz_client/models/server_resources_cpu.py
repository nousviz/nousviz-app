from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ServerResourcesCpu")


@_attrs_define
class ServerResourcesCpu:
    """
    Attributes:
        cpu_count (int):
        cpu_model (None | str | Unset):
    """

    cpu_count: int
    cpu_model: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cpu_count = self.cpu_count

        cpu_model: None | str | Unset
        if isinstance(self.cpu_model, Unset):
            cpu_model = UNSET
        else:
            cpu_model = self.cpu_model

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "cpu_count": cpu_count,
            }
        )
        if cpu_model is not UNSET:
            field_dict["cpu_model"] = cpu_model

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        cpu_count = d.pop("cpu_count")

        def _parse_cpu_model(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        cpu_model = _parse_cpu_model(d.pop("cpu_model", UNSET))

        server_resources_cpu = cls(
            cpu_count=cpu_count,
            cpu_model=cpu_model,
        )

        server_resources_cpu.additional_properties = d
        return server_resources_cpu

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
