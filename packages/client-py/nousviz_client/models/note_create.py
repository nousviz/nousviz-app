from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NoteCreate")


@_attrs_define
class NoteCreate:
    """
    Attributes:
        page_path (str):
        body (str):
        plugin_id (None | str | Unset):
        date_start (None | str | Unset):
        date_end (None | str | Unset):
        pinned (bool | Unset):  Default: False.
    """

    page_path: str
    body: str
    plugin_id: None | str | Unset = UNSET
    date_start: None | str | Unset = UNSET
    date_end: None | str | Unset = UNSET
    pinned: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        page_path = self.page_path

        body = self.body

        plugin_id: None | str | Unset
        if isinstance(self.plugin_id, Unset):
            plugin_id = UNSET
        else:
            plugin_id = self.plugin_id

        date_start: None | str | Unset
        if isinstance(self.date_start, Unset):
            date_start = UNSET
        else:
            date_start = self.date_start

        date_end: None | str | Unset
        if isinstance(self.date_end, Unset):
            date_end = UNSET
        else:
            date_end = self.date_end

        pinned = self.pinned

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "page_path": page_path,
                "body": body,
            }
        )
        if plugin_id is not UNSET:
            field_dict["plugin_id"] = plugin_id
        if date_start is not UNSET:
            field_dict["date_start"] = date_start
        if date_end is not UNSET:
            field_dict["date_end"] = date_end
        if pinned is not UNSET:
            field_dict["pinned"] = pinned

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        page_path = d.pop("page_path")

        body = d.pop("body")

        def _parse_plugin_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        plugin_id = _parse_plugin_id(d.pop("plugin_id", UNSET))

        def _parse_date_start(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        date_start = _parse_date_start(d.pop("date_start", UNSET))

        def _parse_date_end(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        date_end = _parse_date_end(d.pop("date_end", UNSET))

        pinned = d.pop("pinned", UNSET)

        note_create = cls(
            page_path=page_path,
            body=body,
            plugin_id=plugin_id,
            date_start=date_start,
            date_end=date_end,
            pinned=pinned,
        )

        note_create.additional_properties = d
        return note_create

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
