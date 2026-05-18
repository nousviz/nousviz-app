from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.note_entry import NoteEntry


T = TypeVar("T", bound="NotesListResponse")


@_attrs_define
class NotesListResponse:
    """GET /api/notes — pinned-first ordering, optional page-path/plugin filter.

    Attributes:
        notes (list[NoteEntry]):
        count (int):
    """

    notes: list[NoteEntry]
    count: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        notes = []
        for notes_item_data in self.notes:
            notes_item = notes_item_data.to_dict()
            notes.append(notes_item)

        count = self.count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "notes": notes,
                "count": count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.note_entry import NoteEntry

        d = dict(src_dict)
        notes = []
        _notes = d.pop("notes")
        for notes_item_data in _notes:
            notes_item = NoteEntry.from_dict(notes_item_data)

            notes.append(notes_item)

        count = d.pop("count")

        notes_list_response = cls(
            notes=notes,
            count=count,
        )

        notes_list_response.additional_properties = d
        return notes_list_response

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
