from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SyncScheduleBody")


@_attrs_define
class SyncScheduleBody:
    """Per-plugin schedule override.

    B148: cron=None or "" clears the override (falls back to manifest).
    B205 (v0.9.6): friendly form — supply interval_value + interval_unit
    instead of a raw cron expression. The two forms are mutually exclusive
    in a single request.

    Examples:
        {"cron": "*/15 * * * *"}                      raw cron
        {"interval_value": 15, "interval_unit": "minutes"}  friendly form
        {"cron": null}                                 clear override

        Attributes:
            cron (None | str | Unset):
            interval_value (int | None | Unset):
            interval_unit (None | str | Unset):
    """

    cron: None | str | Unset = UNSET
    interval_value: int | None | Unset = UNSET
    interval_unit: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cron: None | str | Unset
        if isinstance(self.cron, Unset):
            cron = UNSET
        else:
            cron = self.cron

        interval_value: int | None | Unset
        if isinstance(self.interval_value, Unset):
            interval_value = UNSET
        else:
            interval_value = self.interval_value

        interval_unit: None | str | Unset
        if isinstance(self.interval_unit, Unset):
            interval_unit = UNSET
        else:
            interval_unit = self.interval_unit

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cron is not UNSET:
            field_dict["cron"] = cron
        if interval_value is not UNSET:
            field_dict["interval_value"] = interval_value
        if interval_unit is not UNSET:
            field_dict["interval_unit"] = interval_unit

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_cron(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        cron = _parse_cron(d.pop("cron", UNSET))

        def _parse_interval_value(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        interval_value = _parse_interval_value(d.pop("interval_value", UNSET))

        def _parse_interval_unit(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        interval_unit = _parse_interval_unit(d.pop("interval_unit", UNSET))

        sync_schedule_body = cls(
            cron=cron,
            interval_value=interval_value,
            interval_unit=interval_unit,
        )

        sync_schedule_body.additional_properties = d
        return sync_schedule_body

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
