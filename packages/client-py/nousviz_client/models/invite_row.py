from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="InviteRow")


@_attrs_define
class InviteRow:
    """A single user_invites row.

    Attributes:
        id (str):
        email (str):
        role (str):
        invited_by (None | str | Unset):
        inviter_email (None | str | Unset):
        inviter_name (None | str | Unset):
        used_at (None | str | Unset):
        expires_at (None | str | Unset):
        created_at (None | str | Unset):
    """

    id: str
    email: str
    role: str
    invited_by: None | str | Unset = UNSET
    inviter_email: None | str | Unset = UNSET
    inviter_name: None | str | Unset = UNSET
    used_at: None | str | Unset = UNSET
    expires_at: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        email = self.email

        role = self.role

        invited_by: None | str | Unset
        if isinstance(self.invited_by, Unset):
            invited_by = UNSET
        else:
            invited_by = self.invited_by

        inviter_email: None | str | Unset
        if isinstance(self.inviter_email, Unset):
            inviter_email = UNSET
        else:
            inviter_email = self.inviter_email

        inviter_name: None | str | Unset
        if isinstance(self.inviter_name, Unset):
            inviter_name = UNSET
        else:
            inviter_name = self.inviter_name

        used_at: None | str | Unset
        if isinstance(self.used_at, Unset):
            used_at = UNSET
        else:
            used_at = self.used_at

        expires_at: None | str | Unset
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        else:
            expires_at = self.expires_at

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "email": email,
                "role": role,
            }
        )
        if invited_by is not UNSET:
            field_dict["invited_by"] = invited_by
        if inviter_email is not UNSET:
            field_dict["inviter_email"] = inviter_email
        if inviter_name is not UNSET:
            field_dict["inviter_name"] = inviter_name
        if used_at is not UNSET:
            field_dict["used_at"] = used_at
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        email = d.pop("email")

        role = d.pop("role")

        def _parse_invited_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        invited_by = _parse_invited_by(d.pop("invited_by", UNSET))

        def _parse_inviter_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        inviter_email = _parse_inviter_email(d.pop("inviter_email", UNSET))

        def _parse_inviter_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        inviter_name = _parse_inviter_name(d.pop("inviter_name", UNSET))

        def _parse_used_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        used_at = _parse_used_at(d.pop("used_at", UNSET))

        def _parse_expires_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        invite_row = cls(
            id=id,
            email=email,
            role=role,
            invited_by=invited_by,
            inviter_email=inviter_email,
            inviter_name=inviter_name,
            used_at=used_at,
            expires_at=expires_at,
            created_at=created_at,
        )

        invite_row.additional_properties = d
        return invite_row

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
