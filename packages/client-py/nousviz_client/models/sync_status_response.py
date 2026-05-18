from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.sync_run_current import SyncRunCurrent
    from ..models.sync_run_failure import SyncRunFailure
    from ..models.sync_run_success import SyncRunSuccess


T = TypeVar("T", bound="SyncStatusResponse")


@_attrs_define
class SyncStatusResponse:
    """GET /api/plugins/{id}/sync/status — composite snapshot for the Sync card.

    `current` is the in-flight run, or null when idle. `last_success` /
    `last_failure` are the most recent terminal runs. `last_sync` mirrors
    `last_success.completed_at` for backward compatibility with pre-v0.9.6
    frontend code.

        Attributes:
            current (None | SyncRunCurrent | Unset):
            last_success (None | SyncRunSuccess | Unset):
            last_failure (None | SyncRunFailure | Unset):
            last_sync (None | str | Unset):
    """

    current: None | SyncRunCurrent | Unset = UNSET
    last_success: None | SyncRunSuccess | Unset = UNSET
    last_failure: None | SyncRunFailure | Unset = UNSET
    last_sync: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.sync_run_current import SyncRunCurrent
        from ..models.sync_run_failure import SyncRunFailure
        from ..models.sync_run_success import SyncRunSuccess

        current: dict[str, Any] | None | Unset
        if isinstance(self.current, Unset):
            current = UNSET
        elif isinstance(self.current, SyncRunCurrent):
            current = self.current.to_dict()
        else:
            current = self.current

        last_success: dict[str, Any] | None | Unset
        if isinstance(self.last_success, Unset):
            last_success = UNSET
        elif isinstance(self.last_success, SyncRunSuccess):
            last_success = self.last_success.to_dict()
        else:
            last_success = self.last_success

        last_failure: dict[str, Any] | None | Unset
        if isinstance(self.last_failure, Unset):
            last_failure = UNSET
        elif isinstance(self.last_failure, SyncRunFailure):
            last_failure = self.last_failure.to_dict()
        else:
            last_failure = self.last_failure

        last_sync: None | str | Unset
        if isinstance(self.last_sync, Unset):
            last_sync = UNSET
        else:
            last_sync = self.last_sync

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if current is not UNSET:
            field_dict["current"] = current
        if last_success is not UNSET:
            field_dict["last_success"] = last_success
        if last_failure is not UNSET:
            field_dict["last_failure"] = last_failure
        if last_sync is not UNSET:
            field_dict["last_sync"] = last_sync

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sync_run_current import SyncRunCurrent
        from ..models.sync_run_failure import SyncRunFailure
        from ..models.sync_run_success import SyncRunSuccess

        d = dict(src_dict)

        def _parse_current(data: object) -> None | SyncRunCurrent | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                current_type_0 = SyncRunCurrent.from_dict(data)

                return current_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SyncRunCurrent | Unset, data)

        current = _parse_current(d.pop("current", UNSET))

        def _parse_last_success(data: object) -> None | SyncRunSuccess | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                last_success_type_0 = SyncRunSuccess.from_dict(data)

                return last_success_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SyncRunSuccess | Unset, data)

        last_success = _parse_last_success(d.pop("last_success", UNSET))

        def _parse_last_failure(data: object) -> None | SyncRunFailure | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                last_failure_type_0 = SyncRunFailure.from_dict(data)

                return last_failure_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SyncRunFailure | Unset, data)

        last_failure = _parse_last_failure(d.pop("last_failure", UNSET))

        def _parse_last_sync(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_sync = _parse_last_sync(d.pop("last_sync", UNSET))

        sync_status_response = cls(
            current=current,
            last_success=last_success,
            last_failure=last_failure,
            last_sync=last_sync,
        )

        sync_status_response.additional_properties = d
        return sync_status_response

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
