from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.share_create_filters import ShareCreateFilters


T = TypeVar("T", bound="ShareCreate")


@_attrs_define
class ShareCreate:
    """
    Attributes:
        page_path (str):
        title (None | str | Unset):
        resource_type (str | Unset):  Default: 'dashboard'.
        filters (ShareCreateFilters | Unset):
        password (None | str | Unset):
        expires_hours (int | Unset):  Default: 168.
    """

    page_path: str
    title: None | str | Unset = UNSET
    resource_type: str | Unset = "dashboard"
    filters: ShareCreateFilters | Unset = UNSET
    password: None | str | Unset = UNSET
    expires_hours: int | Unset = 168
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        page_path = self.page_path

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        resource_type = self.resource_type

        filters: dict[str, Any] | Unset = UNSET
        if not isinstance(self.filters, Unset):
            filters = self.filters.to_dict()

        password: None | str | Unset
        if isinstance(self.password, Unset):
            password = UNSET
        else:
            password = self.password

        expires_hours = self.expires_hours

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "page_path": page_path,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if resource_type is not UNSET:
            field_dict["resource_type"] = resource_type
        if filters is not UNSET:
            field_dict["filters"] = filters
        if password is not UNSET:
            field_dict["password"] = password
        if expires_hours is not UNSET:
            field_dict["expires_hours"] = expires_hours

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.share_create_filters import ShareCreateFilters

        d = dict(src_dict)
        page_path = d.pop("page_path")

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        resource_type = d.pop("resource_type", UNSET)

        _filters = d.pop("filters", UNSET)
        filters: ShareCreateFilters | Unset
        if isinstance(_filters, Unset):
            filters = UNSET
        else:
            filters = ShareCreateFilters.from_dict(_filters)

        def _parse_password(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        password = _parse_password(d.pop("password", UNSET))

        expires_hours = d.pop("expires_hours", UNSET)

        share_create = cls(
            page_path=page_path,
            title=title,
            resource_type=resource_type,
            filters=filters,
            password=password,
            expires_hours=expires_hours,
        )

        share_create.additional_properties = d
        return share_create

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
