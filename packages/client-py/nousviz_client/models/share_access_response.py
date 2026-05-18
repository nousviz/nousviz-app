from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.share_access_response_filters import ShareAccessResponseFilters


T = TypeVar("T", bound="ShareAccessResponse")


@_attrs_define
class ShareAccessResponse:
    """POST /api/shares/{share_id}/access — public landing-page access.

    Returns the page-path + filters needed to render the shared view.
    Filters is a free-form JSONB blob defined by the dashboard author.

        Attributes:
            page_path (str):
            title (None | str | Unset):
            filters (ShareAccessResponseFilters | Unset): Free-form filter state (date range, dimension selections, etc.) —
                dashboard-author-defined shape.
    """

    page_path: str
    title: None | str | Unset = UNSET
    filters: ShareAccessResponseFilters | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        page_path = self.page_path

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        filters: dict[str, Any] | Unset = UNSET
        if not isinstance(self.filters, Unset):
            filters = self.filters.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "page_path": page_path,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if filters is not UNSET:
            field_dict["filters"] = filters

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.share_access_response_filters import ShareAccessResponseFilters

        d = dict(src_dict)
        page_path = d.pop("page_path")

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        _filters = d.pop("filters", UNSET)
        filters: ShareAccessResponseFilters | Unset
        if isinstance(_filters, Unset):
            filters = UNSET
        else:
            filters = ShareAccessResponseFilters.from_dict(_filters)

        share_access_response = cls(
            page_path=page_path,
            title=title,
            filters=filters,
        )

        share_access_response.additional_properties = d
        return share_access_response

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
