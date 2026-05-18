from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JobsDashboardRecentItem")


@_attrs_define
class JobsDashboardRecentItem:
    """B277: a completed job_runs row from the recent-history window.

    Attributes:
        id (int):
        job_id (str):
        status (str):
        started_at (str):
        completed_at (None | str | Unset):
        duration_ms (int | None | Unset):
        error_short (None | str | Unset): First 200 chars of the run's error column, or null.
    """

    id: int
    job_id: str
    status: str
    started_at: str
    completed_at: None | str | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    error_short: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        job_id = self.job_id

        status = self.status

        started_at = self.started_at

        completed_at: None | str | Unset
        if isinstance(self.completed_at, Unset):
            completed_at = UNSET
        else:
            completed_at = self.completed_at

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        error_short: None | str | Unset
        if isinstance(self.error_short, Unset):
            error_short = UNSET
        else:
            error_short = self.error_short

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "job_id": job_id,
                "status": status,
                "started_at": started_at,
            }
        )
        if completed_at is not UNSET:
            field_dict["completed_at"] = completed_at
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms
        if error_short is not UNSET:
            field_dict["error_short"] = error_short

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        job_id = d.pop("job_id")

        status = d.pop("status")

        started_at = d.pop("started_at")

        def _parse_completed_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        completed_at = _parse_completed_at(d.pop("completed_at", UNSET))

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("duration_ms", UNSET))

        def _parse_error_short(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error_short = _parse_error_short(d.pop("error_short", UNSET))

        jobs_dashboard_recent_item = cls(
            id=id,
            job_id=job_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            error_short=error_short,
        )

        jobs_dashboard_recent_item.additional_properties = d
        return jobs_dashboard_recent_item

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
