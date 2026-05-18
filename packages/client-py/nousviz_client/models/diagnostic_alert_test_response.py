from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DiagnosticAlertTestResponse")


@_attrs_define
class DiagnosticAlertTestResponse:
    """POST /api/maintenance/diagnostic-alerts/test.

    Attributes:
        delivered (int): Webhooks the synthetic payload reached successfully.
        subscribed_webhooks (int): Total currently-subscribed webhooks.
    """

    delivered: int
    subscribed_webhooks: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        delivered = self.delivered

        subscribed_webhooks = self.subscribed_webhooks

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "delivered": delivered,
                "subscribed_webhooks": subscribed_webhooks,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        delivered = d.pop("delivered")

        subscribed_webhooks = d.pop("subscribed_webhooks")

        diagnostic_alert_test_response = cls(
            delivered=delivered,
            subscribed_webhooks=subscribed_webhooks,
        )

        diagnostic_alert_test_response.additional_properties = d
        return diagnostic_alert_test_response

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
