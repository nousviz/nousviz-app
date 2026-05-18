from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CustomRoleCreateRequest")


@_attrs_define
class CustomRoleCreateRequest:
    """
    Attributes:
        role (str):
        display_name (str):
        description (None | str | Unset):
        based_on (None | str | Unset):
        permissions (list[str] | None | Unset):
        rank (int | Unset):  Default: 0.
    """

    role: str
    display_name: str
    description: None | str | Unset = UNSET
    based_on: None | str | Unset = UNSET
    permissions: list[str] | None | Unset = UNSET
    rank: int | Unset = 0
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        role = self.role

        display_name = self.display_name

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        based_on: None | str | Unset
        if isinstance(self.based_on, Unset):
            based_on = UNSET
        else:
            based_on = self.based_on

        permissions: list[str] | None | Unset
        if isinstance(self.permissions, Unset):
            permissions = UNSET
        elif isinstance(self.permissions, list):
            permissions = self.permissions

        else:
            permissions = self.permissions

        rank = self.rank

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "role": role,
                "display_name": display_name,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if based_on is not UNSET:
            field_dict["based_on"] = based_on
        if permissions is not UNSET:
            field_dict["permissions"] = permissions
        if rank is not UNSET:
            field_dict["rank"] = rank

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        role = d.pop("role")

        display_name = d.pop("display_name")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_based_on(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        based_on = _parse_based_on(d.pop("based_on", UNSET))

        def _parse_permissions(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                permissions_type_0 = cast(list[str], data)

                return permissions_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        permissions = _parse_permissions(d.pop("permissions", UNSET))

        rank = d.pop("rank", UNSET)

        custom_role_create_request = cls(
            role=role,
            display_name=display_name,
            description=description,
            based_on=based_on,
            permissions=permissions,
            rank=rank,
        )

        custom_role_create_request.additional_properties = d
        return custom_role_create_request

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
