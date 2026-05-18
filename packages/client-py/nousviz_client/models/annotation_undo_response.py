from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.annotation_undo_response_restored_to_type_0 import AnnotationUndoResponseRestoredToType0


T = TypeVar("T", bound="AnnotationUndoResponse")


@_attrs_define
class AnnotationUndoResponse:
    """POST /api/annotations/{annotation_id}/undo.

    Two shapes depending on what was undone:
    - Undoing a 'created' action: `action='archived (creation undone)'`,
      no `restored_to`.
    - Undoing an 'updated' action: `restored_to` carries the snapshot.

        Attributes:
            status (str | Unset): Always 'undone' on success. Default: 'undone'.
            action (None | str | Unset):
            restored_to (AnnotationUndoResponseRestoredToType0 | None | Unset):
    """

    status: str | Unset = "undone"
    action: None | str | Unset = UNSET
    restored_to: AnnotationUndoResponseRestoredToType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.annotation_undo_response_restored_to_type_0 import AnnotationUndoResponseRestoredToType0

        status = self.status

        action: None | str | Unset
        if isinstance(self.action, Unset):
            action = UNSET
        else:
            action = self.action

        restored_to: dict[str, Any] | None | Unset
        if isinstance(self.restored_to, Unset):
            restored_to = UNSET
        elif isinstance(self.restored_to, AnnotationUndoResponseRestoredToType0):
            restored_to = self.restored_to.to_dict()
        else:
            restored_to = self.restored_to

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if status is not UNSET:
            field_dict["status"] = status
        if action is not UNSET:
            field_dict["action"] = action
        if restored_to is not UNSET:
            field_dict["restored_to"] = restored_to

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.annotation_undo_response_restored_to_type_0 import AnnotationUndoResponseRestoredToType0

        d = dict(src_dict)
        status = d.pop("status", UNSET)

        def _parse_action(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        action = _parse_action(d.pop("action", UNSET))

        def _parse_restored_to(data: object) -> AnnotationUndoResponseRestoredToType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                restored_to_type_0 = AnnotationUndoResponseRestoredToType0.from_dict(data)

                return restored_to_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(AnnotationUndoResponseRestoredToType0 | None | Unset, data)

        restored_to = _parse_restored_to(d.pop("restored_to", UNSET))

        annotation_undo_response = cls(
            status=status,
            action=action,
            restored_to=restored_to,
        )

        annotation_undo_response.additional_properties = d
        return annotation_undo_response

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
