from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ShareLink")


@_attrs_define
class ShareLink:
    """Single shared_links row from /api/shares list.

    Attributes:
        share_id (str):
        page_path (str):
        resource_type (str):
        has_password (bool):
        expired (bool): True iff the link's expiry has passed at query time.
        title (None | str | Unset):
        notes (None | str | Unset):
        created_at (None | str | Unset):
        expires_at (None | str | Unset):
        access_count (int | Unset):  Default: 0.
        last_accessed (None | str | Unset):
        revoked (bool | Unset):  Default: False.
    """

    share_id: str
    page_path: str
    resource_type: str
    has_password: bool
    expired: bool
    title: None | str | Unset = UNSET
    notes: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    expires_at: None | str | Unset = UNSET
    access_count: int | Unset = 0
    last_accessed: None | str | Unset = UNSET
    revoked: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        share_id = self.share_id

        page_path = self.page_path

        resource_type = self.resource_type

        has_password = self.has_password

        expired = self.expired

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        notes: None | str | Unset
        if isinstance(self.notes, Unset):
            notes = UNSET
        else:
            notes = self.notes

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        expires_at: None | str | Unset
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        else:
            expires_at = self.expires_at

        access_count = self.access_count

        last_accessed: None | str | Unset
        if isinstance(self.last_accessed, Unset):
            last_accessed = UNSET
        else:
            last_accessed = self.last_accessed

        revoked = self.revoked

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "share_id": share_id,
                "page_path": page_path,
                "resource_type": resource_type,
                "has_password": has_password,
                "expired": expired,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if notes is not UNSET:
            field_dict["notes"] = notes
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at
        if access_count is not UNSET:
            field_dict["access_count"] = access_count
        if last_accessed is not UNSET:
            field_dict["last_accessed"] = last_accessed
        if revoked is not UNSET:
            field_dict["revoked"] = revoked

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        share_id = d.pop("share_id")

        page_path = d.pop("page_path")

        resource_type = d.pop("resource_type")

        has_password = d.pop("has_password")

        expired = d.pop("expired")

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        def _parse_notes(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        notes = _parse_notes(d.pop("notes", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_expires_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

        access_count = d.pop("access_count", UNSET)

        def _parse_last_accessed(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_accessed = _parse_last_accessed(d.pop("last_accessed", UNSET))

        revoked = d.pop("revoked", UNSET)

        share_link = cls(
            share_id=share_id,
            page_path=page_path,
            resource_type=resource_type,
            has_password=has_password,
            expired=expired,
            title=title,
            notes=notes,
            created_at=created_at,
            expires_at=expires_at,
            access_count=access_count,
            last_accessed=last_accessed,
            revoked=revoked,
        )

        share_link.additional_properties = d
        return share_link

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
