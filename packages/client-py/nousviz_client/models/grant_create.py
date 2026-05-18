from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GrantCreate")


@_attrs_define
class GrantCreate:
    """
    Attributes:
        principal_kind (str): 'role' or 'user'.
        principal_id (str): Role name or user_id.
        permission (str): e.g. dashboards.read, fusions.write.
        note (None | str | Unset):
    """

    principal_kind: str
    principal_id: str
    permission: str
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        principal_kind = self.principal_kind

        principal_id = self.principal_id

        permission = self.permission

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "principal_kind": principal_kind,
                "principal_id": principal_id,
                "permission": permission,
            }
        )
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        principal_kind = d.pop("principal_kind")

        principal_id = d.pop("principal_id")

        permission = d.pop("permission")

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        grant_create = cls(
            principal_kind=principal_kind,
            principal_id=principal_id,
            permission=permission,
            note=note,
        )

        grant_create.additional_properties = d
        return grant_create

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
