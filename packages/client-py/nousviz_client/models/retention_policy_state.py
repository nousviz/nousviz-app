from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="RetentionPolicyState")


@_attrs_define
class RetentionPolicyState:
    """One row in the /settings/maintenance retention table.

    `rows_total` and `rows_would_prune` are computed live (cached at
    request time, no caching layer above) so the operator sees an
    accurate "click 'Run now' and N rows will be deleted" preview.

        Attributes:
            key (str): Canonical policy identifier (e.g. 'app_logs', 'job_runs:success').
            table (str): SQL table the policy prunes.
            field (str): Timestamp field used for the retention cutoff.
            description (str): Human-readable summary of what the policy keeps.
            retention_days (int): Current retention threshold in days. 0 means immediate purge of rows matching
                `additional_where`.
            paused (bool): When true, the cron worker skips this policy. Default for every policy at install.
            rows_total (int): Current total rows in the policy's scope (bounded by additional_where if any).
            rows_would_prune (int): Rows that exceed the retention threshold and would be deleted on the next run.
            last_run_at (None | str | Unset):
            last_run_rows_deleted (int | None | Unset):
            last_run_error (None | str | Unset):
            updated_at (None | str | Unset):
    """

    key: str
    table: str
    field: str
    description: str
    retention_days: int
    paused: bool
    rows_total: int
    rows_would_prune: int
    last_run_at: None | str | Unset = UNSET
    last_run_rows_deleted: int | None | Unset = UNSET
    last_run_error: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        key = self.key

        table = self.table

        field = self.field

        description = self.description

        retention_days = self.retention_days

        paused = self.paused

        rows_total = self.rows_total

        rows_would_prune = self.rows_would_prune

        last_run_at: None | str | Unset
        if isinstance(self.last_run_at, Unset):
            last_run_at = UNSET
        else:
            last_run_at = self.last_run_at

        last_run_rows_deleted: int | None | Unset
        if isinstance(self.last_run_rows_deleted, Unset):
            last_run_rows_deleted = UNSET
        else:
            last_run_rows_deleted = self.last_run_rows_deleted

        last_run_error: None | str | Unset
        if isinstance(self.last_run_error, Unset):
            last_run_error = UNSET
        else:
            last_run_error = self.last_run_error

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "key": key,
                "table": table,
                "field": field,
                "description": description,
                "retention_days": retention_days,
                "paused": paused,
                "rows_total": rows_total,
                "rows_would_prune": rows_would_prune,
            }
        )
        if last_run_at is not UNSET:
            field_dict["last_run_at"] = last_run_at
        if last_run_rows_deleted is not UNSET:
            field_dict["last_run_rows_deleted"] = last_run_rows_deleted
        if last_run_error is not UNSET:
            field_dict["last_run_error"] = last_run_error
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        key = d.pop("key")

        table = d.pop("table")

        field = d.pop("field")

        description = d.pop("description")

        retention_days = d.pop("retention_days")

        paused = d.pop("paused")

        rows_total = d.pop("rows_total")

        rows_would_prune = d.pop("rows_would_prune")

        def _parse_last_run_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_run_at = _parse_last_run_at(d.pop("last_run_at", UNSET))

        def _parse_last_run_rows_deleted(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        last_run_rows_deleted = _parse_last_run_rows_deleted(d.pop("last_run_rows_deleted", UNSET))

        def _parse_last_run_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_run_error = _parse_last_run_error(d.pop("last_run_error", UNSET))

        def _parse_updated_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        retention_policy_state = cls(
            key=key,
            table=table,
            field=field,
            description=description,
            retention_days=retention_days,
            paused=paused,
            rows_total=rows_total,
            rows_would_prune=rows_would_prune,
            last_run_at=last_run_at,
            last_run_rows_deleted=last_run_rows_deleted,
            last_run_error=last_run_error,
            updated_at=updated_at,
        )

        retention_policy_state.additional_properties = d
        return retention_policy_state

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
