from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PluginAccessPayload")


@_attrs_define
class PluginAccessPayload:
    """
    Attributes:
        mode (str):
        plugin_ids (list[str] | Unset):
    """

    mode: str
    plugin_ids: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        mode = self.mode

        plugin_ids: list[str] | Unset = UNSET
        if not isinstance(self.plugin_ids, Unset):
            plugin_ids = self.plugin_ids

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "mode": mode,
            }
        )
        if plugin_ids is not UNSET:
            field_dict["plugin_ids"] = plugin_ids

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        mode = d.pop("mode")

        plugin_ids = cast(list[str], d.pop("plugin_ids", UNSET))

        plugin_access_payload = cls(
            mode=mode,
            plugin_ids=plugin_ids,
        )

        plugin_access_payload.additional_properties = d
        return plugin_access_payload

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
