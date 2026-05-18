from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.save_connections_health_block import SaveConnectionsHealthBlock


T = TypeVar("T", bound="PluginConnectionsSaveResponse")


@_attrs_define
class PluginConnectionsSaveResponse:
    """POST /api/plugins/{id}/connections — confirms write + post-save health check.

    Attributes:
        ok (bool | Unset):  Default: True.
        health (None | SaveConnectionsHealthBlock | Unset): Result of the plugin's health_check hook, or null if none
            declared.
    """

    ok: bool | Unset = True
    health: None | SaveConnectionsHealthBlock | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.save_connections_health_block import SaveConnectionsHealthBlock

        ok = self.ok

        health: dict[str, Any] | None | Unset
        if isinstance(self.health, Unset):
            health = UNSET
        elif isinstance(self.health, SaveConnectionsHealthBlock):
            health = self.health.to_dict()
        else:
            health = self.health

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if ok is not UNSET:
            field_dict["ok"] = ok
        if health is not UNSET:
            field_dict["health"] = health

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.save_connections_health_block import SaveConnectionsHealthBlock

        d = dict(src_dict)
        ok = d.pop("ok", UNSET)

        def _parse_health(data: object) -> None | SaveConnectionsHealthBlock | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                health_type_0 = SaveConnectionsHealthBlock.from_dict(data)

                return health_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SaveConnectionsHealthBlock | Unset, data)

        health = _parse_health(d.pop("health", UNSET))

        plugin_connections_save_response = cls(
            ok=ok,
            health=health,
        )

        plugin_connections_save_response.additional_properties = d
        return plugin_connections_save_response

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
