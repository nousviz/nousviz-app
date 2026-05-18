from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.annotation_history_entry_snapshot_type_0 import AnnotationHistoryEntrySnapshotType0


T = TypeVar("T", bound="AnnotationHistoryEntry")


@_attrs_define
class AnnotationHistoryEntry:
    """A single annotation_history row — one change to an annotation.

    Attributes:
        id (str):
        action (str): 'created' | 'updated' | 'deleted' | 'restored'.
        changed_by (None | str | Unset):
        changed_at (None | str | Unset):
        snapshot (AnnotationHistoryEntrySnapshotType0 | None | Unset): Annotation state before the change (or after, for
            'created').
    """

    id: str
    action: str
    changed_by: None | str | Unset = UNSET
    changed_at: None | str | Unset = UNSET
    snapshot: AnnotationHistoryEntrySnapshotType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.annotation_history_entry_snapshot_type_0 import AnnotationHistoryEntrySnapshotType0

        id = self.id

        action = self.action

        changed_by: None | str | Unset
        if isinstance(self.changed_by, Unset):
            changed_by = UNSET
        else:
            changed_by = self.changed_by

        changed_at: None | str | Unset
        if isinstance(self.changed_at, Unset):
            changed_at = UNSET
        else:
            changed_at = self.changed_at

        snapshot: dict[str, Any] | None | Unset
        if isinstance(self.snapshot, Unset):
            snapshot = UNSET
        elif isinstance(self.snapshot, AnnotationHistoryEntrySnapshotType0):
            snapshot = self.snapshot.to_dict()
        else:
            snapshot = self.snapshot

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "action": action,
            }
        )
        if changed_by is not UNSET:
            field_dict["changed_by"] = changed_by
        if changed_at is not UNSET:
            field_dict["changed_at"] = changed_at
        if snapshot is not UNSET:
            field_dict["snapshot"] = snapshot

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.annotation_history_entry_snapshot_type_0 import AnnotationHistoryEntrySnapshotType0

        d = dict(src_dict)
        id = d.pop("id")

        action = d.pop("action")

        def _parse_changed_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        changed_by = _parse_changed_by(d.pop("changed_by", UNSET))

        def _parse_changed_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        changed_at = _parse_changed_at(d.pop("changed_at", UNSET))

        def _parse_snapshot(data: object) -> AnnotationHistoryEntrySnapshotType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                snapshot_type_0 = AnnotationHistoryEntrySnapshotType0.from_dict(data)

                return snapshot_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(AnnotationHistoryEntrySnapshotType0 | None | Unset, data)

        snapshot = _parse_snapshot(d.pop("snapshot", UNSET))

        annotation_history_entry = cls(
            id=id,
            action=action,
            changed_by=changed_by,
            changed_at=changed_at,
            snapshot=snapshot,
        )

        annotation_history_entry.additional_properties = d
        return annotation_history_entry

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
