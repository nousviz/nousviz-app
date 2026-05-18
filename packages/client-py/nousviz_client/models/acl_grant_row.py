from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AclGrantRow")


@_attrs_define
class AclGrantRow:
    """A single resource_acls row.

    Attributes:
        id (int):
        resource_type (str):
        resource_id (str):
        principal_kind (str):
        principal_id (str):
        permission (str):
        granted_by (None | str | Unset):
        note (None | str | Unset):
        created_at (None | str | Unset):
    """

    id: int
    resource_type: str
    resource_id: str
    principal_kind: str
    principal_id: str
    permission: str
    granted_by: None | str | Unset = UNSET
    note: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        resource_type = self.resource_type

        resource_id = self.resource_id

        principal_kind = self.principal_kind

        principal_id = self.principal_id

        permission = self.permission

        granted_by: None | str | Unset
        if isinstance(self.granted_by, Unset):
            granted_by = UNSET
        else:
            granted_by = self.granted_by

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

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
                "resource_type": resource_type,
                "resource_id": resource_id,
                "principal_kind": principal_kind,
                "principal_id": principal_id,
                "permission": permission,
            }
        )
        if granted_by is not UNSET:
            field_dict["granted_by"] = granted_by
        if note is not UNSET:
            field_dict["note"] = note
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        resource_type = d.pop("resource_type")

        resource_id = d.pop("resource_id")

        principal_kind = d.pop("principal_kind")

        principal_id = d.pop("principal_id")

        permission = d.pop("permission")

        def _parse_granted_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        granted_by = _parse_granted_by(d.pop("granted_by", UNSET))

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        acl_grant_row = cls(
            id=id,
            resource_type=resource_type,
            resource_id=resource_id,
            principal_kind=principal_kind,
            principal_id=principal_id,
            permission=permission,
            granted_by=granted_by,
            note=note,
            created_at=created_at,
        )

        acl_grant_row.additional_properties = d
        return acl_grant_row

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
