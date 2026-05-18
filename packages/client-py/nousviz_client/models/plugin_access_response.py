from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PluginAccessResponse")


@_attrs_define
class PluginAccessResponse:
    """GET / PUT /api/auth/users/{user_id}/plugin-access — current
    allowlist state for the user.

    `mode='all'` means zero ACL rows (unrestricted). `mode='specific'`
    means one or more rows; `plugin_ids` lists the slugs the user is
    allowed to see (utility plugins always pass through regardless).

        Attributes:
            mode (str): 'all' | 'specific'
            plugin_ids (list[str] | Unset):
            role (None | str | Unset): The target user's current role, for UI display.
            unrestricted_by_role (bool | Unset): True when the target user's role (admin/superadmin) makes them unrestricted
                regardless of ACL rows. UI greys out the editor. Default: False.
    """

    mode: str
    plugin_ids: list[str] | Unset = UNSET
    role: None | str | Unset = UNSET
    unrestricted_by_role: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        mode = self.mode

        plugin_ids: list[str] | Unset = UNSET
        if not isinstance(self.plugin_ids, Unset):
            plugin_ids = self.plugin_ids

        role: None | str | Unset
        if isinstance(self.role, Unset):
            role = UNSET
        else:
            role = self.role

        unrestricted_by_role = self.unrestricted_by_role

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "mode": mode,
            }
        )
        if plugin_ids is not UNSET:
            field_dict["plugin_ids"] = plugin_ids
        if role is not UNSET:
            field_dict["role"] = role
        if unrestricted_by_role is not UNSET:
            field_dict["unrestricted_by_role"] = unrestricted_by_role

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        mode = d.pop("mode")

        plugin_ids = cast(list[str], d.pop("plugin_ids", UNSET))

        def _parse_role(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        role = _parse_role(d.pop("role", UNSET))

        unrestricted_by_role = d.pop("unrestricted_by_role", UNSET)

        plugin_access_response = cls(
            mode=mode,
            plugin_ids=plugin_ids,
            role=role,
            unrestricted_by_role=unrestricted_by_role,
        )

        plugin_access_response.additional_properties = d
        return plugin_access_response

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
