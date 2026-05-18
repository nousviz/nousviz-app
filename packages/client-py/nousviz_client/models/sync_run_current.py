from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.sync_run_current_progress import SyncRunCurrentProgress


T = TypeVar("T", bound="SyncRunCurrent")


@_attrs_define
class SyncRunCurrent:
    """In-flight sync run — populated when status IN ('queued','running','cancelling').

    Attributes:
        run_id (int):
        status (str):
        elapsed_sec (int):
        source (None | str | Unset): Who triggered this run (manual/scheduler/api).
        started_at (None | str | Unset):
        heartbeat_at (None | str | Unset):
        progress (SyncRunCurrentProgress | Unset): Live progress payload from the worker — shape is plugin-defined.
    """

    run_id: int
    status: str
    elapsed_sec: int
    source: None | str | Unset = UNSET
    started_at: None | str | Unset = UNSET
    heartbeat_at: None | str | Unset = UNSET
    progress: SyncRunCurrentProgress | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        run_id = self.run_id

        status = self.status

        elapsed_sec = self.elapsed_sec

        source: None | str | Unset
        if isinstance(self.source, Unset):
            source = UNSET
        else:
            source = self.source

        started_at: None | str | Unset
        if isinstance(self.started_at, Unset):
            started_at = UNSET
        else:
            started_at = self.started_at

        heartbeat_at: None | str | Unset
        if isinstance(self.heartbeat_at, Unset):
            heartbeat_at = UNSET
        else:
            heartbeat_at = self.heartbeat_at

        progress: dict[str, Any] | Unset = UNSET
        if not isinstance(self.progress, Unset):
            progress = self.progress.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "run_id": run_id,
                "status": status,
                "elapsed_sec": elapsed_sec,
            }
        )
        if source is not UNSET:
            field_dict["source"] = source
        if started_at is not UNSET:
            field_dict["started_at"] = started_at
        if heartbeat_at is not UNSET:
            field_dict["heartbeat_at"] = heartbeat_at
        if progress is not UNSET:
            field_dict["progress"] = progress

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sync_run_current_progress import SyncRunCurrentProgress

        d = dict(src_dict)
        run_id = d.pop("run_id")

        status = d.pop("status")

        elapsed_sec = d.pop("elapsed_sec")

        def _parse_source(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        source = _parse_source(d.pop("source", UNSET))

        def _parse_started_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        started_at = _parse_started_at(d.pop("started_at", UNSET))

        def _parse_heartbeat_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        heartbeat_at = _parse_heartbeat_at(d.pop("heartbeat_at", UNSET))

        _progress = d.pop("progress", UNSET)
        progress: SyncRunCurrentProgress | Unset
        if isinstance(_progress, Unset):
            progress = UNSET
        else:
            progress = SyncRunCurrentProgress.from_dict(_progress)

        sync_run_current = cls(
            run_id=run_id,
            status=status,
            elapsed_sec=elapsed_sec,
            source=source,
            started_at=started_at,
            heartbeat_at=heartbeat_at,
            progress=progress,
        )

        sync_run_current.additional_properties = d
        return sync_run_current

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
