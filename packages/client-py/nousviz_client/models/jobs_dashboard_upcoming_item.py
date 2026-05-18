from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JobsDashboardUpcomingItem")


@_attrs_define
class JobsDashboardUpcomingItem:
    """B277: an upcoming scheduled fire with collision prediction.

    Attributes:
        plugin_id (str):
        schedule_cron (str):
        next_fire_at (str):
        ms_until_fire (int):
        avg_duration_ms (int | None | Unset):
        may_overlap (bool | Unset): True when avg_duration_ms exceeds 90% of ms_until_fire. Default: False.
    """

    plugin_id: str
    schedule_cron: str
    next_fire_at: str
    ms_until_fire: int
    avg_duration_ms: int | None | Unset = UNSET
    may_overlap: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        schedule_cron = self.schedule_cron

        next_fire_at = self.next_fire_at

        ms_until_fire = self.ms_until_fire

        avg_duration_ms: int | None | Unset
        if isinstance(self.avg_duration_ms, Unset):
            avg_duration_ms = UNSET
        else:
            avg_duration_ms = self.avg_duration_ms

        may_overlap = self.may_overlap

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "schedule_cron": schedule_cron,
                "next_fire_at": next_fire_at,
                "ms_until_fire": ms_until_fire,
            }
        )
        if avg_duration_ms is not UNSET:
            field_dict["avg_duration_ms"] = avg_duration_ms
        if may_overlap is not UNSET:
            field_dict["may_overlap"] = may_overlap

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        schedule_cron = d.pop("schedule_cron")

        next_fire_at = d.pop("next_fire_at")

        ms_until_fire = d.pop("ms_until_fire")

        def _parse_avg_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        avg_duration_ms = _parse_avg_duration_ms(d.pop("avg_duration_ms", UNSET))

        may_overlap = d.pop("may_overlap", UNSET)

        jobs_dashboard_upcoming_item = cls(
            plugin_id=plugin_id,
            schedule_cron=schedule_cron,
            next_fire_at=next_fire_at,
            ms_until_fire=ms_until_fire,
            avg_duration_ms=avg_duration_ms,
            may_overlap=may_overlap,
        )

        jobs_dashboard_upcoming_item.additional_properties = d
        return jobs_dashboard_upcoming_item

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
