from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.connection_health_history_entry import ConnectionHealthHistoryEntry


T = TypeVar("T", bound="ConnectionHealthHistoryResponse")


@_attrs_define
class ConnectionHealthHistoryResponse:
    """GET /api/connections/{conn_id}/health-history — last 20 health checks.

    Attributes:
        status (None | str | Unset): Most recent health_status value.
        last_check (None | str | Unset):
        history (list[ConnectionHealthHistoryEntry] | Unset): Newest-first; capped at 20 entries.
    """

    status: None | str | Unset = UNSET
    last_check: None | str | Unset = UNSET
    history: list[ConnectionHealthHistoryEntry] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

        last_check: None | str | Unset
        if isinstance(self.last_check, Unset):
            last_check = UNSET
        else:
            last_check = self.last_check

        history: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.history, Unset):
            history = []
            for history_item_data in self.history:
                history_item = history_item_data.to_dict()
                history.append(history_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if status is not UNSET:
            field_dict["status"] = status
        if last_check is not UNSET:
            field_dict["last_check"] = last_check
        if history is not UNSET:
            field_dict["history"] = history

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.connection_health_history_entry import ConnectionHealthHistoryEntry

        d = dict(src_dict)

        def _parse_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_last_check(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_check = _parse_last_check(d.pop("last_check", UNSET))

        _history = d.pop("history", UNSET)
        history: list[ConnectionHealthHistoryEntry] | Unset = UNSET
        if _history is not UNSET:
            history = []
            for history_item_data in _history:
                history_item = ConnectionHealthHistoryEntry.from_dict(history_item_data)

                history.append(history_item)

        connection_health_history_response = cls(
            status=status,
            last_check=last_check,
            history=history,
        )

        connection_health_history_response.additional_properties = d
        return connection_health_history_response

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
