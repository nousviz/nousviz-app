from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ShareDetailResponse")


@_attrs_define
class ShareDetailResponse:
    """GET /api/shares/{share_id} — public metadata for the share landing page.

    Returns 410 (gone) for revoked or expired links — the response below
    is the success path only.

        Attributes:
            share_id (str):
            page_path (str):
            resource_type (str):
            has_password (bool):
            title (None | str | Unset):
            expires_at (None | str | Unset):
    """

    share_id: str
    page_path: str
    resource_type: str
    has_password: bool
    title: None | str | Unset = UNSET
    expires_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        share_id = self.share_id

        page_path = self.page_path

        resource_type = self.resource_type

        has_password = self.has_password

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        expires_at: None | str | Unset
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        else:
            expires_at = self.expires_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "share_id": share_id,
                "page_path": page_path,
                "resource_type": resource_type,
                "has_password": has_password,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        share_id = d.pop("share_id")

        page_path = d.pop("page_path")

        resource_type = d.pop("resource_type")

        has_password = d.pop("has_password")

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        def _parse_expires_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

        share_detail_response = cls(
            share_id=share_id,
            page_path=page_path,
            resource_type=resource_type,
            has_password=has_password,
            title=title,
            expires_at=expires_at,
        )

        share_detail_response.additional_properties = d
        return share_detail_response

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
