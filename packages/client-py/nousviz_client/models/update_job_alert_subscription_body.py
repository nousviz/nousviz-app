from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="UpdateJobAlertSubscriptionBody")


@_attrs_define
class UpdateJobAlertSubscriptionBody:
    """PUT /api/maintenance/job-alerts/{id}. Pass only the fields you're changing.

    Attributes:
        on_status (list[str] | None | Unset):
        enabled (bool | None | Unset):
    """

    on_status: list[str] | None | Unset = UNSET
    enabled: bool | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        on_status: list[str] | None | Unset
        if isinstance(self.on_status, Unset):
            on_status = UNSET
        elif isinstance(self.on_status, list):
            on_status = self.on_status

        else:
            on_status = self.on_status

        enabled: bool | None | Unset
        if isinstance(self.enabled, Unset):
            enabled = UNSET
        else:
            enabled = self.enabled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if on_status is not UNSET:
            field_dict["on_status"] = on_status
        if enabled is not UNSET:
            field_dict["enabled"] = enabled

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_on_status(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                on_status_type_0 = cast(list[str], data)

                return on_status_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        on_status = _parse_on_status(d.pop("on_status", UNSET))

        def _parse_enabled(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        enabled = _parse_enabled(d.pop("enabled", UNSET))

        update_job_alert_subscription_body = cls(
            on_status=on_status,
            enabled=enabled,
        )

        update_job_alert_subscription_body.additional_properties = d
        return update_job_alert_subscription_body

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
