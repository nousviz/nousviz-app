from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PluginStat")


@_attrs_define
class PluginStat:
    """
    Attributes:
        id (str):
        table_count (int):
        total_size_mb (float):
        total_rows (int):
        last_sync_at (None | str | Unset):
        sync_schedule_cron (None | str | Unset):
    """

    id: str
    table_count: int
    total_size_mb: float
    total_rows: int
    last_sync_at: None | str | Unset = UNSET
    sync_schedule_cron: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        table_count = self.table_count

        total_size_mb = self.total_size_mb

        total_rows = self.total_rows

        last_sync_at: None | str | Unset
        if isinstance(self.last_sync_at, Unset):
            last_sync_at = UNSET
        else:
            last_sync_at = self.last_sync_at

        sync_schedule_cron: None | str | Unset
        if isinstance(self.sync_schedule_cron, Unset):
            sync_schedule_cron = UNSET
        else:
            sync_schedule_cron = self.sync_schedule_cron

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "table_count": table_count,
                "total_size_mb": total_size_mb,
                "total_rows": total_rows,
            }
        )
        if last_sync_at is not UNSET:
            field_dict["last_sync_at"] = last_sync_at
        if sync_schedule_cron is not UNSET:
            field_dict["sync_schedule_cron"] = sync_schedule_cron

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        table_count = d.pop("table_count")

        total_size_mb = d.pop("total_size_mb")

        total_rows = d.pop("total_rows")

        def _parse_last_sync_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_sync_at = _parse_last_sync_at(d.pop("last_sync_at", UNSET))

        def _parse_sync_schedule_cron(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sync_schedule_cron = _parse_sync_schedule_cron(d.pop("sync_schedule_cron", UNSET))

        plugin_stat = cls(
            id=id,
            table_count=table_count,
            total_size_mb=total_size_mb,
            total_rows=total_rows,
            last_sync_at=last_sync_at,
            sync_schedule_cron=sync_schedule_cron,
        )

        plugin_stat.additional_properties = d
        return plugin_stat

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
