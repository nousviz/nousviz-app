from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JobSchedulerState")


@_attrs_define
class JobSchedulerState:
    """sync_schedule_registry row attached to plugin sync jobs (B150).

    Surfaced under JobEntry.scheduler — tells the operator UI whether
    the v0.9.3 scheduler is actively tracking this plugin and when it
    last enqueued a run.

        Attributes:
            cron_expression (None | str | Unset):
            cron_source (None | str | Unset): 'manifest' | 'override'.
            next_fire_at (None | str | Unset):
            last_enqueued_at (None | str | Unset):
            last_run_id (int | None | Unset):
            last_error (None | str | Unset):
            age_sec (int | None | Unset): Seconds since the registry row was last touched. <300 means scheduler is alive.
    """

    cron_expression: None | str | Unset = UNSET
    cron_source: None | str | Unset = UNSET
    next_fire_at: None | str | Unset = UNSET
    last_enqueued_at: None | str | Unset = UNSET
    last_run_id: int | None | Unset = UNSET
    last_error: None | str | Unset = UNSET
    age_sec: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cron_expression: None | str | Unset
        if isinstance(self.cron_expression, Unset):
            cron_expression = UNSET
        else:
            cron_expression = self.cron_expression

        cron_source: None | str | Unset
        if isinstance(self.cron_source, Unset):
            cron_source = UNSET
        else:
            cron_source = self.cron_source

        next_fire_at: None | str | Unset
        if isinstance(self.next_fire_at, Unset):
            next_fire_at = UNSET
        else:
            next_fire_at = self.next_fire_at

        last_enqueued_at: None | str | Unset
        if isinstance(self.last_enqueued_at, Unset):
            last_enqueued_at = UNSET
        else:
            last_enqueued_at = self.last_enqueued_at

        last_run_id: int | None | Unset
        if isinstance(self.last_run_id, Unset):
            last_run_id = UNSET
        else:
            last_run_id = self.last_run_id

        last_error: None | str | Unset
        if isinstance(self.last_error, Unset):
            last_error = UNSET
        else:
            last_error = self.last_error

        age_sec: int | None | Unset
        if isinstance(self.age_sec, Unset):
            age_sec = UNSET
        else:
            age_sec = self.age_sec

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cron_expression is not UNSET:
            field_dict["cron_expression"] = cron_expression
        if cron_source is not UNSET:
            field_dict["cron_source"] = cron_source
        if next_fire_at is not UNSET:
            field_dict["next_fire_at"] = next_fire_at
        if last_enqueued_at is not UNSET:
            field_dict["last_enqueued_at"] = last_enqueued_at
        if last_run_id is not UNSET:
            field_dict["last_run_id"] = last_run_id
        if last_error is not UNSET:
            field_dict["last_error"] = last_error
        if age_sec is not UNSET:
            field_dict["age_sec"] = age_sec

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_cron_expression(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        cron_expression = _parse_cron_expression(d.pop("cron_expression", UNSET))

        def _parse_cron_source(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        cron_source = _parse_cron_source(d.pop("cron_source", UNSET))

        def _parse_next_fire_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        next_fire_at = _parse_next_fire_at(d.pop("next_fire_at", UNSET))

        def _parse_last_enqueued_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_enqueued_at = _parse_last_enqueued_at(d.pop("last_enqueued_at", UNSET))

        def _parse_last_run_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        last_run_id = _parse_last_run_id(d.pop("last_run_id", UNSET))

        def _parse_last_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_error = _parse_last_error(d.pop("last_error", UNSET))

        def _parse_age_sec(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        age_sec = _parse_age_sec(d.pop("age_sec", UNSET))

        job_scheduler_state = cls(
            cron_expression=cron_expression,
            cron_source=cron_source,
            next_fire_at=next_fire_at,
            last_enqueued_at=last_enqueued_at,
            last_run_id=last_run_id,
            last_error=last_error,
            age_sec=age_sec,
        )

        job_scheduler_state.additional_properties = d
        return job_scheduler_state

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
