from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SyncScheduleSetResponse")


@_attrs_define
class SyncScheduleSetResponse:
    """POST /api/plugins/{id}/sync-schedule — write or clear an override.

    Attributes:
        saved (bool):
        override_cron (None | str | Unset): The newly-stored override, or null when clearing.
        preview_next_fires (list[str] | Unset): Up to 5 ISO-8601 firing times from now under the new cron.
        note (None | str | Unset):
    """

    saved: bool
    override_cron: None | str | Unset = UNSET
    preview_next_fires: list[str] | Unset = UNSET
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        saved = self.saved

        override_cron: None | str | Unset
        if isinstance(self.override_cron, Unset):
            override_cron = UNSET
        else:
            override_cron = self.override_cron

        preview_next_fires: list[str] | Unset = UNSET
        if not isinstance(self.preview_next_fires, Unset):
            preview_next_fires = self.preview_next_fires

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "saved": saved,
            }
        )
        if override_cron is not UNSET:
            field_dict["override_cron"] = override_cron
        if preview_next_fires is not UNSET:
            field_dict["preview_next_fires"] = preview_next_fires
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        saved = d.pop("saved")

        def _parse_override_cron(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        override_cron = _parse_override_cron(d.pop("override_cron", UNSET))

        preview_next_fires = cast(list[str], d.pop("preview_next_fires", UNSET))

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        sync_schedule_set_response = cls(
            saved=saved,
            override_cron=override_cron,
            preview_next_fires=preview_next_fires,
            note=note,
        )

        sync_schedule_set_response.additional_properties = d
        return sync_schedule_set_response

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
