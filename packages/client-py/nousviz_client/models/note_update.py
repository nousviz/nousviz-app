from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NoteUpdate")


@_attrs_define
class NoteUpdate:
    """
    Attributes:
        body (None | str | Unset):
        date_start (None | str | Unset):
        date_end (None | str | Unset):
        pinned (bool | None | Unset):
        resolved (bool | None | Unset):
        archived (bool | None | Unset):
    """

    body: None | str | Unset = UNSET
    date_start: None | str | Unset = UNSET
    date_end: None | str | Unset = UNSET
    pinned: bool | None | Unset = UNSET
    resolved: bool | None | Unset = UNSET
    archived: bool | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        body: None | str | Unset
        if isinstance(self.body, Unset):
            body = UNSET
        else:
            body = self.body

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

        pinned: bool | None | Unset
        if isinstance(self.pinned, Unset):
            pinned = UNSET
        else:
            pinned = self.pinned

        resolved: bool | None | Unset
        if isinstance(self.resolved, Unset):
            resolved = UNSET
        else:
            resolved = self.resolved

        archived: bool | None | Unset
        if isinstance(self.archived, Unset):
            archived = UNSET
        else:
            archived = self.archived

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if body is not UNSET:
            field_dict["body"] = body
        if date_start is not UNSET:
            field_dict["date_start"] = date_start
        if date_end is not UNSET:
            field_dict["date_end"] = date_end
        if pinned is not UNSET:
            field_dict["pinned"] = pinned
        if resolved is not UNSET:
            field_dict["resolved"] = resolved
        if archived is not UNSET:
            field_dict["archived"] = archived

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_body(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        body = _parse_body(d.pop("body", UNSET))

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

        def _parse_pinned(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        pinned = _parse_pinned(d.pop("pinned", UNSET))

        def _parse_resolved(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        resolved = _parse_resolved(d.pop("resolved", UNSET))

        def _parse_archived(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        archived = _parse_archived(d.pop("archived", UNSET))

        note_update = cls(
            body=body,
            date_start=date_start,
            date_end=date_end,
            pinned=pinned,
            resolved=resolved,
            archived=archived,
        )

        note_update.additional_properties = d
        return note_update

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
