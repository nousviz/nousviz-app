from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.invite_request_plugin_access_type_0 import InviteRequestPluginAccessType0


T = TypeVar("T", bound="InviteRequest")


@_attrs_define
class InviteRequest:
    """
    Attributes:
        email (str):
        role (str | Unset):  Default: 'analyst'.
        plugin_access (InviteRequestPluginAccessType0 | None | Unset):
    """

    email: str
    role: str | Unset = "analyst"
    plugin_access: InviteRequestPluginAccessType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.invite_request_plugin_access_type_0 import InviteRequestPluginAccessType0

        email = self.email

        role = self.role

        plugin_access: dict[str, Any] | None | Unset
        if isinstance(self.plugin_access, Unset):
            plugin_access = UNSET
        elif isinstance(self.plugin_access, InviteRequestPluginAccessType0):
            plugin_access = self.plugin_access.to_dict()
        else:
            plugin_access = self.plugin_access

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "email": email,
            }
        )
        if role is not UNSET:
            field_dict["role"] = role
        if plugin_access is not UNSET:
            field_dict["plugin_access"] = plugin_access

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.invite_request_plugin_access_type_0 import InviteRequestPluginAccessType0

        d = dict(src_dict)
        email = d.pop("email")

        role = d.pop("role", UNSET)

        def _parse_plugin_access(data: object) -> InviteRequestPluginAccessType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                plugin_access_type_0 = InviteRequestPluginAccessType0.from_dict(data)

                return plugin_access_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(InviteRequestPluginAccessType0 | None | Unset, data)

        plugin_access = _parse_plugin_access(d.pop("plugin_access", UNSET))

        invite_request = cls(
            email=email,
            role=role,
            plugin_access=plugin_access,
        )

        invite_request.additional_properties = d
        return invite_request

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
