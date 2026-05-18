from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.log_entry_detail_type_0 import LogEntryDetailType0


T = TypeVar("T", bound="LogEntry")


@_attrs_define
class LogEntry:
    """A single app_logs row as returned by /api/admin/logs.

    `actor_email` and `run_status` are joined in from users / job_runs.
    `actor_user_id` is the actor's UUID as a string (or null when the
    log entry has no associated actor — e.g. system-emitted events).

        Attributes:
            id (int):
            level (str): 'info' | 'warning' | 'error' | etc.
            source (str): Log source label, e.g. 'plugin', 'plugin_route', 'rbac', 'sync'.
            message (str):
            detail (LogEntryDetailType0 | None | Unset): Structured JSONB detail payload — shape depends on the source.
            created_at (None | str | Unset):
            plugin_id (None | str | Unset):
            actor_user_id (None | str | Unset):
            run_id (int | None | Unset):
            actor_email (None | str | Unset):
            run_status (None | str | Unset):
    """

    id: int
    level: str
    source: str
    message: str
    detail: LogEntryDetailType0 | None | Unset = UNSET
    created_at: None | str | Unset = UNSET
    plugin_id: None | str | Unset = UNSET
    actor_user_id: None | str | Unset = UNSET
    run_id: int | None | Unset = UNSET
    actor_email: None | str | Unset = UNSET
    run_status: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.log_entry_detail_type_0 import LogEntryDetailType0

        id = self.id

        level = self.level

        source = self.source

        message = self.message

        detail: dict[str, Any] | None | Unset
        if isinstance(self.detail, Unset):
            detail = UNSET
        elif isinstance(self.detail, LogEntryDetailType0):
            detail = self.detail.to_dict()
        else:
            detail = self.detail

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        plugin_id: None | str | Unset
        if isinstance(self.plugin_id, Unset):
            plugin_id = UNSET
        else:
            plugin_id = self.plugin_id

        actor_user_id: None | str | Unset
        if isinstance(self.actor_user_id, Unset):
            actor_user_id = UNSET
        else:
            actor_user_id = self.actor_user_id

        run_id: int | None | Unset
        if isinstance(self.run_id, Unset):
            run_id = UNSET
        else:
            run_id = self.run_id

        actor_email: None | str | Unset
        if isinstance(self.actor_email, Unset):
            actor_email = UNSET
        else:
            actor_email = self.actor_email

        run_status: None | str | Unset
        if isinstance(self.run_status, Unset):
            run_status = UNSET
        else:
            run_status = self.run_status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "level": level,
                "source": source,
                "message": message,
            }
        )
        if detail is not UNSET:
            field_dict["detail"] = detail
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if plugin_id is not UNSET:
            field_dict["plugin_id"] = plugin_id
        if actor_user_id is not UNSET:
            field_dict["actor_user_id"] = actor_user_id
        if run_id is not UNSET:
            field_dict["run_id"] = run_id
        if actor_email is not UNSET:
            field_dict["actor_email"] = actor_email
        if run_status is not UNSET:
            field_dict["run_status"] = run_status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.log_entry_detail_type_0 import LogEntryDetailType0

        d = dict(src_dict)
        id = d.pop("id")

        level = d.pop("level")

        source = d.pop("source")

        message = d.pop("message")

        def _parse_detail(data: object) -> LogEntryDetailType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                detail_type_0 = LogEntryDetailType0.from_dict(data)

                return detail_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(LogEntryDetailType0 | None | Unset, data)

        detail = _parse_detail(d.pop("detail", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_plugin_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        plugin_id = _parse_plugin_id(d.pop("plugin_id", UNSET))

        def _parse_actor_user_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        actor_user_id = _parse_actor_user_id(d.pop("actor_user_id", UNSET))

        def _parse_run_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        run_id = _parse_run_id(d.pop("run_id", UNSET))

        def _parse_actor_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        actor_email = _parse_actor_email(d.pop("actor_email", UNSET))

        def _parse_run_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        run_status = _parse_run_status(d.pop("run_status", UNSET))

        log_entry = cls(
            id=id,
            level=level,
            source=source,
            message=message,
            detail=detail,
            created_at=created_at,
            plugin_id=plugin_id,
            actor_user_id=actor_user_id,
            run_id=run_id,
            actor_email=actor_email,
            run_status=run_status,
        )

        log_entry.additional_properties = d
        return log_entry

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
