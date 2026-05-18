from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="RoleOverrideResponse")


@_attrs_define
class RoleOverrideResponse:
    """POST /api/system/role-overrides — newly written override row.

    Attributes:
        id (int):
        role (str):
        permission (str):
        kind (str): 'grant' | 'revoke'.
        created_by (str):
        created_at (str):
        note (None | str | Unset):
    """

    id: int
    role: str
    permission: str
    kind: str
    created_by: str
    created_at: str
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        role = self.role

        permission = self.permission

        kind = self.kind

        created_by = self.created_by

        created_at = self.created_at

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "role": role,
                "permission": permission,
                "kind": kind,
                "created_by": created_by,
                "created_at": created_at,
            }
        )
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        role = d.pop("role")

        permission = d.pop("permission")

        kind = d.pop("kind")

        created_by = d.pop("created_by")

        created_at = d.pop("created_at")

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        role_override_response = cls(
            id=id,
            role=role,
            permission=permission,
            kind=kind,
            created_by=created_by,
            created_at=created_at,
            note=note,
        )

        role_override_response.additional_properties = d
        return role_override_response

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
