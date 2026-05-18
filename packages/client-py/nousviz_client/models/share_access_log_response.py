from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.share_access_log_entry import ShareAccessLogEntry


T = TypeVar("T", bound="ShareAccessLogResponse")


@_attrs_define
class ShareAccessLogResponse:
    """GET /api/shares/{share_id}/log — last 50 access attempts.

    Attributes:
        log (list[ShareAccessLogEntry]):
        count (int):
    """

    log: list[ShareAccessLogEntry]
    count: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        log = []
        for log_item_data in self.log:
            log_item = log_item_data.to_dict()
            log.append(log_item)

        count = self.count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "log": log,
                "count": count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.share_access_log_entry import ShareAccessLogEntry

        d = dict(src_dict)
        log = []
        _log = d.pop("log")
        for log_item_data in _log:
            log_item = ShareAccessLogEntry.from_dict(log_item_data)

            log.append(log_item)

        count = d.pop("count")

        share_access_log_response = cls(
            log=log,
            count=count,
        )

        share_access_log_response.additional_properties = d
        return share_access_log_response

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
