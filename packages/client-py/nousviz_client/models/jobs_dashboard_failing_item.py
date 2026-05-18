from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JobsDashboardFailingItem")


@_attrs_define
class JobsDashboardFailingItem:
    """B277 (v0.9.11.16.1): a job with ANY errors in the last 24h.

    Threshold widened from > 50% error rate to errors > 0 per operator
    UX feedback: sporadic failures matter and should surface for
    investigation. Ordered server-side by `last_error_at` DESC so the
    frontend can lead with the most recent failure.

        Attributes:
            job_id (str):
            runs_24h (int):
            errors_24h (int):
            error_rate_pct (float):
            last_error (None | str | Unset):
            last_error_at (None | str | Unset): ISO timestamp of the most recent error — anchors the deep-link into
                /system/logs.
    """

    job_id: str
    runs_24h: int
    errors_24h: int
    error_rate_pct: float
    last_error: None | str | Unset = UNSET
    last_error_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        job_id = self.job_id

        runs_24h = self.runs_24h

        errors_24h = self.errors_24h

        error_rate_pct = self.error_rate_pct

        last_error: None | str | Unset
        if isinstance(self.last_error, Unset):
            last_error = UNSET
        else:
            last_error = self.last_error

        last_error_at: None | str | Unset
        if isinstance(self.last_error_at, Unset):
            last_error_at = UNSET
        else:
            last_error_at = self.last_error_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "job_id": job_id,
                "runs_24h": runs_24h,
                "errors_24h": errors_24h,
                "error_rate_pct": error_rate_pct,
            }
        )
        if last_error is not UNSET:
            field_dict["last_error"] = last_error
        if last_error_at is not UNSET:
            field_dict["last_error_at"] = last_error_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        job_id = d.pop("job_id")

        runs_24h = d.pop("runs_24h")

        errors_24h = d.pop("errors_24h")

        error_rate_pct = d.pop("error_rate_pct")

        def _parse_last_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_error = _parse_last_error(d.pop("last_error", UNSET))

        def _parse_last_error_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_error_at = _parse_last_error_at(d.pop("last_error_at", UNSET))

        jobs_dashboard_failing_item = cls(
            job_id=job_id,
            runs_24h=runs_24h,
            errors_24h=errors_24h,
            error_rate_pct=error_rate_pct,
            last_error=last_error,
            last_error_at=last_error_at,
        )

        jobs_dashboard_failing_item.additional_properties = d
        return jobs_dashboard_failing_item

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
