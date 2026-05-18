from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.job_run_row_details_type_0 import JobRunRowDetailsType0
    from ..models.job_run_row_progress_type_0 import JobRunRowProgressType0


T = TypeVar("T", bound="JobRunRow")


@_attrs_define
class JobRunRow:
    """A single job_runs row — used by /api/jobs/runs and /api/jobs/{run_id}.

    Datetimes are ISO-8601 strings. Extra fields are allowed because the
    detail endpoint returns more columns than the list endpoint
    (claimed_by, heartbeat_at, progress, etc).

        Attributes:
            id (int):
            job_id (str):
            status (str): 'queued' | 'running' | 'success' | 'error' | 'timeout' | 'cancelled' | 'cancelling' | 'paused' |
                'skipped'.
            started_at (None | str | Unset):
            completed_at (None | str | Unset):
            duration_ms (int | None | Unset):
            rows_written (int | None | Unset):
            error (None | str | Unset):
            source (None | str | Unset):
            exit_code (int | None | Unset):
            details (JobRunRowDetailsType0 | None | Unset):
            progress (JobRunRowProgressType0 | None | Unset):
            cancelled_at (None | str | Unset):
            paused_at (None | str | Unset):
            claimed_by (None | str | Unset):
            claimed_at (None | str | Unset):
            heartbeat_at (None | str | Unset):
    """

    id: int
    job_id: str
    status: str
    started_at: None | str | Unset = UNSET
    completed_at: None | str | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    rows_written: int | None | Unset = UNSET
    error: None | str | Unset = UNSET
    source: None | str | Unset = UNSET
    exit_code: int | None | Unset = UNSET
    details: JobRunRowDetailsType0 | None | Unset = UNSET
    progress: JobRunRowProgressType0 | None | Unset = UNSET
    cancelled_at: None | str | Unset = UNSET
    paused_at: None | str | Unset = UNSET
    claimed_by: None | str | Unset = UNSET
    claimed_at: None | str | Unset = UNSET
    heartbeat_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.job_run_row_details_type_0 import JobRunRowDetailsType0
        from ..models.job_run_row_progress_type_0 import JobRunRowProgressType0

        id = self.id

        job_id = self.job_id

        status = self.status

        started_at: None | str | Unset
        if isinstance(self.started_at, Unset):
            started_at = UNSET
        else:
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

        rows_written: int | None | Unset
        if isinstance(self.rows_written, Unset):
            rows_written = UNSET
        else:
            rows_written = self.rows_written

        error: None | str | Unset
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        source: None | str | Unset
        if isinstance(self.source, Unset):
            source = UNSET
        else:
            source = self.source

        exit_code: int | None | Unset
        if isinstance(self.exit_code, Unset):
            exit_code = UNSET
        else:
            exit_code = self.exit_code

        details: dict[str, Any] | None | Unset
        if isinstance(self.details, Unset):
            details = UNSET
        elif isinstance(self.details, JobRunRowDetailsType0):
            details = self.details.to_dict()
        else:
            details = self.details

        progress: dict[str, Any] | None | Unset
        if isinstance(self.progress, Unset):
            progress = UNSET
        elif isinstance(self.progress, JobRunRowProgressType0):
            progress = self.progress.to_dict()
        else:
            progress = self.progress

        cancelled_at: None | str | Unset
        if isinstance(self.cancelled_at, Unset):
            cancelled_at = UNSET
        else:
            cancelled_at = self.cancelled_at

        paused_at: None | str | Unset
        if isinstance(self.paused_at, Unset):
            paused_at = UNSET
        else:
            paused_at = self.paused_at

        claimed_by: None | str | Unset
        if isinstance(self.claimed_by, Unset):
            claimed_by = UNSET
        else:
            claimed_by = self.claimed_by

        claimed_at: None | str | Unset
        if isinstance(self.claimed_at, Unset):
            claimed_at = UNSET
        else:
            claimed_at = self.claimed_at

        heartbeat_at: None | str | Unset
        if isinstance(self.heartbeat_at, Unset):
            heartbeat_at = UNSET
        else:
            heartbeat_at = self.heartbeat_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "job_id": job_id,
                "status": status,
            }
        )
        if started_at is not UNSET:
            field_dict["started_at"] = started_at
        if completed_at is not UNSET:
            field_dict["completed_at"] = completed_at
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms
        if rows_written is not UNSET:
            field_dict["rows_written"] = rows_written
        if error is not UNSET:
            field_dict["error"] = error
        if source is not UNSET:
            field_dict["source"] = source
        if exit_code is not UNSET:
            field_dict["exit_code"] = exit_code
        if details is not UNSET:
            field_dict["details"] = details
        if progress is not UNSET:
            field_dict["progress"] = progress
        if cancelled_at is not UNSET:
            field_dict["cancelled_at"] = cancelled_at
        if paused_at is not UNSET:
            field_dict["paused_at"] = paused_at
        if claimed_by is not UNSET:
            field_dict["claimed_by"] = claimed_by
        if claimed_at is not UNSET:
            field_dict["claimed_at"] = claimed_at
        if heartbeat_at is not UNSET:
            field_dict["heartbeat_at"] = heartbeat_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.job_run_row_details_type_0 import JobRunRowDetailsType0
        from ..models.job_run_row_progress_type_0 import JobRunRowProgressType0

        d = dict(src_dict)
        id = d.pop("id")

        job_id = d.pop("job_id")

        status = d.pop("status")

        def _parse_started_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        started_at = _parse_started_at(d.pop("started_at", UNSET))

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

        def _parse_rows_written(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        rows_written = _parse_rows_written(d.pop("rows_written", UNSET))

        def _parse_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error = _parse_error(d.pop("error", UNSET))

        def _parse_source(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        source = _parse_source(d.pop("source", UNSET))

        def _parse_exit_code(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        exit_code = _parse_exit_code(d.pop("exit_code", UNSET))

        def _parse_details(data: object) -> JobRunRowDetailsType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                details_type_0 = JobRunRowDetailsType0.from_dict(data)

                return details_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(JobRunRowDetailsType0 | None | Unset, data)

        details = _parse_details(d.pop("details", UNSET))

        def _parse_progress(data: object) -> JobRunRowProgressType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                progress_type_0 = JobRunRowProgressType0.from_dict(data)

                return progress_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(JobRunRowProgressType0 | None | Unset, data)

        progress = _parse_progress(d.pop("progress", UNSET))

        def _parse_cancelled_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        cancelled_at = _parse_cancelled_at(d.pop("cancelled_at", UNSET))

        def _parse_paused_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        paused_at = _parse_paused_at(d.pop("paused_at", UNSET))

        def _parse_claimed_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        claimed_by = _parse_claimed_by(d.pop("claimed_by", UNSET))

        def _parse_claimed_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        claimed_at = _parse_claimed_at(d.pop("claimed_at", UNSET))

        def _parse_heartbeat_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        heartbeat_at = _parse_heartbeat_at(d.pop("heartbeat_at", UNSET))

        job_run_row = cls(
            id=id,
            job_id=job_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            rows_written=rows_written,
            error=error,
            source=source,
            exit_code=exit_code,
            details=details,
            progress=progress,
            cancelled_at=cancelled_at,
            paused_at=paused_at,
            claimed_by=claimed_by,
            claimed_at=claimed_at,
            heartbeat_at=heartbeat_at,
        )

        job_run_row.additional_properties = d
        return job_run_row

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
