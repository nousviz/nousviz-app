from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="HealthRecordResponse")


@_attrs_define
class HealthRecordResponse:
    """POST /api/health/record — new snapshot persisted.

    Attributes:
        level (str): 'healthy' | 'warning' | 'error'.
        checks (int): Count of checks in this snapshot.
        status (str | Unset): Always 'recorded' on success. Default: 'recorded'.
    """

    level: str
    checks: int
    status: str | Unset = "recorded"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        level = self.level

        checks = self.checks

        status = self.status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "level": level,
                "checks": checks,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        level = d.pop("level")

        checks = d.pop("checks")

        status = d.pop("status", UNSET)

        health_record_response = cls(
            level=level,
            checks=checks,
            status=status,
        )

        health_record_response.additional_properties = d
        return health_record_response

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
