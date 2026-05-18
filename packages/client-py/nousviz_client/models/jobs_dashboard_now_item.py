from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JobsDashboardNowItem")


@_attrs_define
class JobsDashboardNowItem:
    """B277: a row in the dashboard's NOW section — a currently-running
    or queued job with elapsed time + collision-prediction context.

    v0.9.11.16.4 adds heartbeat liveness so callers can distinguish
    a live worker from an orphaned 'running' row.

        Attributes:
            id (int):
            job_id (str):
            status (str): 'running' | 'queued' | 'cancelling'.
            started_at (str):
            elapsed_ms (int):
            schedule_cron (None | str | Unset):
            next_fire_at (None | str | Unset):
            will_overlap_next (bool | Unset): True when elapsed already exceeds (next_fire_at - started_at). Default: False.
            heartbeat_at (None | str | Unset): ISO timestamp of the worker's most recent heartbeat write. Null until the row
                is claimed.
            heartbeat_age_sec (int | None | Unset): Seconds since heartbeat_at (server-computed). Null when heartbeat_at is
                null.
            worker_alive (bool | Unset): True iff the worker heartbeated within the last 90s. Force-cancel is gated on this
                being false for running rows. Default: False.
    """

    id: int
    job_id: str
    status: str
    started_at: str
    elapsed_ms: int
    schedule_cron: None | str | Unset = UNSET
    next_fire_at: None | str | Unset = UNSET
    will_overlap_next: bool | Unset = False
    heartbeat_at: None | str | Unset = UNSET
    heartbeat_age_sec: int | None | Unset = UNSET
    worker_alive: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        job_id = self.job_id

        status = self.status

        started_at = self.started_at

        elapsed_ms = self.elapsed_ms

        schedule_cron: None | str | Unset
        if isinstance(self.schedule_cron, Unset):
            schedule_cron = UNSET
        else:
            schedule_cron = self.schedule_cron

        next_fire_at: None | str | Unset
        if isinstance(self.next_fire_at, Unset):
            next_fire_at = UNSET
        else:
            next_fire_at = self.next_fire_at

        will_overlap_next = self.will_overlap_next

        heartbeat_at: None | str | Unset
        if isinstance(self.heartbeat_at, Unset):
            heartbeat_at = UNSET
        else:
            heartbeat_at = self.heartbeat_at

        heartbeat_age_sec: int | None | Unset
        if isinstance(self.heartbeat_age_sec, Unset):
            heartbeat_age_sec = UNSET
        else:
            heartbeat_age_sec = self.heartbeat_age_sec

        worker_alive = self.worker_alive

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "job_id": job_id,
                "status": status,
                "started_at": started_at,
                "elapsed_ms": elapsed_ms,
            }
        )
        if schedule_cron is not UNSET:
            field_dict["schedule_cron"] = schedule_cron
        if next_fire_at is not UNSET:
            field_dict["next_fire_at"] = next_fire_at
        if will_overlap_next is not UNSET:
            field_dict["will_overlap_next"] = will_overlap_next
        if heartbeat_at is not UNSET:
            field_dict["heartbeat_at"] = heartbeat_at
        if heartbeat_age_sec is not UNSET:
            field_dict["heartbeat_age_sec"] = heartbeat_age_sec
        if worker_alive is not UNSET:
            field_dict["worker_alive"] = worker_alive

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        job_id = d.pop("job_id")

        status = d.pop("status")

        started_at = d.pop("started_at")

        elapsed_ms = d.pop("elapsed_ms")

        def _parse_schedule_cron(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        schedule_cron = _parse_schedule_cron(d.pop("schedule_cron", UNSET))

        def _parse_next_fire_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        next_fire_at = _parse_next_fire_at(d.pop("next_fire_at", UNSET))

        will_overlap_next = d.pop("will_overlap_next", UNSET)

        def _parse_heartbeat_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        heartbeat_at = _parse_heartbeat_at(d.pop("heartbeat_at", UNSET))

        def _parse_heartbeat_age_sec(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        heartbeat_age_sec = _parse_heartbeat_age_sec(d.pop("heartbeat_age_sec", UNSET))

        worker_alive = d.pop("worker_alive", UNSET)

        jobs_dashboard_now_item = cls(
            id=id,
            job_id=job_id,
            status=status,
            started_at=started_at,
            elapsed_ms=elapsed_ms,
            schedule_cron=schedule_cron,
            next_fire_at=next_fire_at,
            will_overlap_next=will_overlap_next,
            heartbeat_at=heartbeat_at,
            heartbeat_age_sec=heartbeat_age_sec,
            worker_alive=worker_alive,
        )

        jobs_dashboard_now_item.additional_properties = d
        return jobs_dashboard_now_item

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
