from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PluginAuditEntry")


@_attrs_define
class PluginAuditEntry:
    """A single plugin_audit_log row.

    Attributes:
        plugin_id (str):
        action (str):
        detail (Any | None | Unset):
        ip_address (None | str | Unset):
        created_at (None | str | Unset):
        user_name (None | str | Unset):
    """

    plugin_id: str
    action: str
    detail: Any | None | Unset = UNSET
    ip_address: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    user_name: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        action = self.action

        detail: Any | None | Unset
        if isinstance(self.detail, Unset):
            detail = UNSET
        else:
            detail = self.detail

        ip_address: None | str | Unset
        if isinstance(self.ip_address, Unset):
            ip_address = UNSET
        else:
            ip_address = self.ip_address

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        user_name: None | str | Unset
        if isinstance(self.user_name, Unset):
            user_name = UNSET
        else:
            user_name = self.user_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "action": action,
            }
        )
        if detail is not UNSET:
            field_dict["detail"] = detail
        if ip_address is not UNSET:
            field_dict["ip_address"] = ip_address
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if user_name is not UNSET:
            field_dict["user_name"] = user_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        action = d.pop("action")

        def _parse_detail(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        detail = _parse_detail(d.pop("detail", UNSET))

        def _parse_ip_address(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        ip_address = _parse_ip_address(d.pop("ip_address", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_user_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        user_name = _parse_user_name(d.pop("user_name", UNSET))

        plugin_audit_entry = cls(
            plugin_id=plugin_id,
            action=action,
            detail=detail,
            ip_address=ip_address,
            created_at=created_at,
            user_name=user_name,
        )

        plugin_audit_entry.additional_properties = d
        return plugin_audit_entry

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
