from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.diagnostic_alert_subscription import DiagnosticAlertSubscription


T = TypeVar("T", bound="DiagnosticAlertSubscriptionListResponse")


@_attrs_define
class DiagnosticAlertSubscriptionListResponse:
    """GET /api/maintenance/diagnostic-alerts/subscriptions.

    Attributes:
        subscriptions (list[DiagnosticAlertSubscription]):
    """

    subscriptions: list[DiagnosticAlertSubscription]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subscriptions = []
        for subscriptions_item_data in self.subscriptions:
            subscriptions_item = subscriptions_item_data.to_dict()
            subscriptions.append(subscriptions_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "subscriptions": subscriptions,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.diagnostic_alert_subscription import DiagnosticAlertSubscription

        d = dict(src_dict)
        subscriptions = []
        _subscriptions = d.pop("subscriptions")
        for subscriptions_item_data in _subscriptions:
            subscriptions_item = DiagnosticAlertSubscription.from_dict(subscriptions_item_data)

            subscriptions.append(subscriptions_item)

        diagnostic_alert_subscription_list_response = cls(
            subscriptions=subscriptions,
        )

        diagnostic_alert_subscription_list_response.additional_properties = d
        return diagnostic_alert_subscription_list_response

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
