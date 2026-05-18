from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ConnectionHealthCheckResponse")


@_attrs_define
class ConnectionHealthCheckResponse:
    """POST /api/connections/{conn_id}/health-check — probe + persist.

    Attributes:
        status (str): 'connected' | 'error'.
        detail (str):
        checked_at (str): ISO-8601 timestamp of the check.
    """

    status: str
    detail: str
    checked_at: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        detail = self.detail

        checked_at = self.checked_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "detail": detail,
                "checked_at": checked_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = d.pop("status")

        detail = d.pop("detail")

        checked_at = d.pop("checked_at")

        connection_health_check_response = cls(
            status=status,
            detail=detail,
            checked_at=checked_at,
        )

        connection_health_check_response.additional_properties = d
        return connection_health_check_response

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
