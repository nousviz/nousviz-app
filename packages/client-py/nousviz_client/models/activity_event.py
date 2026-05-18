from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.activity_event_detail import ActivityEventDetail


T = TypeVar("T", bound="ActivityEvent")


@_attrs_define
class ActivityEvent:
    """
    Attributes:
        action (str):
        category (str | Unset):  Default: 'general'.
        page_path (None | str | Unset):
        plugin_id (None | str | Unset):
        detail (ActivityEventDetail | Unset):
        duration_ms (int | None | Unset):
    """

    action: str
    category: str | Unset = "general"
    page_path: None | str | Unset = UNSET
    plugin_id: None | str | Unset = UNSET
    detail: ActivityEventDetail | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        action = self.action

        category = self.category

        page_path: None | str | Unset
        if isinstance(self.page_path, Unset):
            page_path = UNSET
        else:
            page_path = self.page_path

        plugin_id: None | str | Unset
        if isinstance(self.plugin_id, Unset):
            plugin_id = UNSET
        else:
            plugin_id = self.plugin_id

        detail: dict[str, Any] | Unset = UNSET
        if not isinstance(self.detail, Unset):
            detail = self.detail.to_dict()

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "action": action,
            }
        )
        if category is not UNSET:
            field_dict["category"] = category
        if page_path is not UNSET:
            field_dict["page_path"] = page_path
        if plugin_id is not UNSET:
            field_dict["plugin_id"] = plugin_id
        if detail is not UNSET:
            field_dict["detail"] = detail
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.activity_event_detail import ActivityEventDetail

        d = dict(src_dict)
        action = d.pop("action")

        category = d.pop("category", UNSET)

        def _parse_page_path(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        page_path = _parse_page_path(d.pop("page_path", UNSET))

        def _parse_plugin_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        plugin_id = _parse_plugin_id(d.pop("plugin_id", UNSET))

        _detail = d.pop("detail", UNSET)
        detail: ActivityEventDetail | Unset
        if isinstance(_detail, Unset):
            detail = UNSET
        else:
            detail = ActivityEventDetail.from_dict(_detail)

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("duration_ms", UNSET))

        activity_event = cls(
            action=action,
            category=category,
            page_path=page_path,
            plugin_id=plugin_id,
            detail=detail,
            duration_ms=duration_ms,
        )

        activity_event.additional_properties = d
        return activity_event

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
