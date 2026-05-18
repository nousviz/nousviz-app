from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SyncStat")


@_attrs_define
class SyncStat:
    """
    Attributes:
        plugin_id (str):
        schedule_cron (str):
        schedule_interval_seconds (int):
        runs_24h (int):
        errors_24h (int):
        cpu_load_pct_estimate (float): (avg_duration_ms × runs_24h) / 86_400_000 × 100, capped at 100. % of one CPU
            continuously consumed by this sync.
        avg_duration_ms (int | None | Unset):
        max_duration_ms (int | None | Unset):
    """

    plugin_id: str
    schedule_cron: str
    schedule_interval_seconds: int
    runs_24h: int
    errors_24h: int
    cpu_load_pct_estimate: float
    avg_duration_ms: int | None | Unset = UNSET
    max_duration_ms: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        schedule_cron = self.schedule_cron

        schedule_interval_seconds = self.schedule_interval_seconds

        runs_24h = self.runs_24h

        errors_24h = self.errors_24h

        cpu_load_pct_estimate = self.cpu_load_pct_estimate

        avg_duration_ms: int | None | Unset
        if isinstance(self.avg_duration_ms, Unset):
            avg_duration_ms = UNSET
        else:
            avg_duration_ms = self.avg_duration_ms

        max_duration_ms: int | None | Unset
        if isinstance(self.max_duration_ms, Unset):
            max_duration_ms = UNSET
        else:
            max_duration_ms = self.max_duration_ms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "schedule_cron": schedule_cron,
                "schedule_interval_seconds": schedule_interval_seconds,
                "runs_24h": runs_24h,
                "errors_24h": errors_24h,
                "cpu_load_pct_estimate": cpu_load_pct_estimate,
            }
        )
        if avg_duration_ms is not UNSET:
            field_dict["avg_duration_ms"] = avg_duration_ms
        if max_duration_ms is not UNSET:
            field_dict["max_duration_ms"] = max_duration_ms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        schedule_cron = d.pop("schedule_cron")

        schedule_interval_seconds = d.pop("schedule_interval_seconds")

        runs_24h = d.pop("runs_24h")

        errors_24h = d.pop("errors_24h")

        cpu_load_pct_estimate = d.pop("cpu_load_pct_estimate")

        def _parse_avg_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        avg_duration_ms = _parse_avg_duration_ms(d.pop("avg_duration_ms", UNSET))

        def _parse_max_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        max_duration_ms = _parse_max_duration_ms(d.pop("max_duration_ms", UNSET))

        sync_stat = cls(
            plugin_id=plugin_id,
            schedule_cron=schedule_cron,
            schedule_interval_seconds=schedule_interval_seconds,
            runs_24h=runs_24h,
            errors_24h=errors_24h,
            cpu_load_pct_estimate=cpu_load_pct_estimate,
            avg_duration_ms=avg_duration_ms,
            max_duration_ms=max_duration_ms,
        )

        sync_stat.additional_properties = d
        return sync_stat

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
