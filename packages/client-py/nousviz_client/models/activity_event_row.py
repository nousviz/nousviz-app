from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ActivityEventRow")


@_attrs_define
class ActivityEventRow:
    """A single activity_events row.

    Has many optional columns added over time; extra='allow' keeps the
    model honest as new columns land.

        Attributes:
            id (Any | None | Unset):
            action (None | str | Unset):
            category (None | str | Unset):
            page_path (None | str | Unset):
            plugin_id (None | str | Unset):
            detail (Any | None | Unset):
            duration_ms (int | None | Unset):
            ip_address (None | str | Unset):
            user_agent (None | str | Unset):
            user_id (None | str | Unset):
            created_at (None | str | Unset):
    """

    id: Any | None | Unset = UNSET
    action: None | str | Unset = UNSET
    category: None | str | Unset = UNSET
    page_path: None | str | Unset = UNSET
    plugin_id: None | str | Unset = UNSET
    detail: Any | None | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    ip_address: None | str | Unset = UNSET
    user_agent: None | str | Unset = UNSET
    user_id: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: Any | None | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        action: None | str | Unset
        if isinstance(self.action, Unset):
            action = UNSET
        else:
            action = self.action

        category: None | str | Unset
        if isinstance(self.category, Unset):
            category = UNSET
        else:
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

        detail: Any | None | Unset
        if isinstance(self.detail, Unset):
            detail = UNSET
        else:
            detail = self.detail

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        ip_address: None | str | Unset
        if isinstance(self.ip_address, Unset):
            ip_address = UNSET
        else:
            ip_address = self.ip_address

        user_agent: None | str | Unset
        if isinstance(self.user_agent, Unset):
            user_agent = UNSET
        else:
            user_agent = self.user_agent

        user_id: None | str | Unset
        if isinstance(self.user_id, Unset):
            user_id = UNSET
        else:
            user_id = self.user_id

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if action is not UNSET:
            field_dict["action"] = action
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
        if ip_address is not UNSET:
            field_dict["ip_address"] = ip_address
        if user_agent is not UNSET:
            field_dict["user_agent"] = user_agent
        if user_id is not UNSET:
            field_dict["user_id"] = user_id
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_id(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_action(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        action = _parse_action(d.pop("action", UNSET))

        def _parse_category(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        category = _parse_category(d.pop("category", UNSET))

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

        def _parse_detail(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        detail = _parse_detail(d.pop("detail", UNSET))

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("duration_ms", UNSET))

        def _parse_ip_address(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        ip_address = _parse_ip_address(d.pop("ip_address", UNSET))

        def _parse_user_agent(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        user_agent = _parse_user_agent(d.pop("user_agent", UNSET))

        def _parse_user_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        user_id = _parse_user_id(d.pop("user_id", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        activity_event_row = cls(
            id=id,
            action=action,
            category=category,
            page_path=page_path,
            plugin_id=plugin_id,
            detail=detail,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id,
            created_at=created_at,
        )

        activity_event_row.additional_properties = d
        return activity_event_row

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
