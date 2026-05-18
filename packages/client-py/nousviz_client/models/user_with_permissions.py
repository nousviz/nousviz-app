from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="UserWithPermissions")


@_attrs_define
class UserWithPermissions:
    """Per-user audit row in the matrix UI's Users tab.

    Attributes:
        id (str):
        email (str):
        is_active (bool):
        name (None | str | Unset):
        role (None | str | Unset):
        permissions (list[str] | Unset): Resolved permission set for this user's role.
        last_activity_at (None | str | Unset):
        last_activity_route (None | str | Unset):
    """

    id: str
    email: str
    is_active: bool
    name: None | str | Unset = UNSET
    role: None | str | Unset = UNSET
    permissions: list[str] | Unset = UNSET
    last_activity_at: None | str | Unset = UNSET
    last_activity_route: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        email = self.email

        is_active = self.is_active

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        role: None | str | Unset
        if isinstance(self.role, Unset):
            role = UNSET
        else:
            role = self.role

        permissions: list[str] | Unset = UNSET
        if not isinstance(self.permissions, Unset):
            permissions = self.permissions

        last_activity_at: None | str | Unset
        if isinstance(self.last_activity_at, Unset):
            last_activity_at = UNSET
        else:
            last_activity_at = self.last_activity_at

        last_activity_route: None | str | Unset
        if isinstance(self.last_activity_route, Unset):
            last_activity_route = UNSET
        else:
            last_activity_route = self.last_activity_route

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "email": email,
                "is_active": is_active,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name
        if role is not UNSET:
            field_dict["role"] = role
        if permissions is not UNSET:
            field_dict["permissions"] = permissions
        if last_activity_at is not UNSET:
            field_dict["last_activity_at"] = last_activity_at
        if last_activity_route is not UNSET:
            field_dict["last_activity_route"] = last_activity_route

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        email = d.pop("email")

        is_active = d.pop("is_active")

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_role(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        role = _parse_role(d.pop("role", UNSET))

        permissions = cast(list[str], d.pop("permissions", UNSET))

        def _parse_last_activity_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_activity_at = _parse_last_activity_at(d.pop("last_activity_at", UNSET))

        def _parse_last_activity_route(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_activity_route = _parse_last_activity_route(d.pop("last_activity_route", UNSET))

        user_with_permissions = cls(
            id=id,
            email=email,
            is_active=is_active,
            name=name,
            role=role,
            permissions=permissions,
            last_activity_at=last_activity_at,
            last_activity_route=last_activity_route,
        )

        user_with_permissions.additional_properties = d
        return user_with_permissions

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
