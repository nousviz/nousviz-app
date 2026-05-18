from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="CreateJobAlertSubscriptionBody")


@_attrs_define
class CreateJobAlertSubscriptionBody:
    """POST /api/maintenance/job-alerts.

    Attributes:
        plugin_id (str): '*' for any plugin, or a specific plugin slug.
        on_status (list[str]): Statuses to alert on. Allowed values: 'error', 'timeout', 'cancelled'.
        webhook_id (str): UUID of an outbound webhook_endpoints row.
    """

    plugin_id: str
    on_status: list[str]
    webhook_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        on_status = self.on_status

        webhook_id = self.webhook_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "on_status": on_status,
                "webhook_id": webhook_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        on_status = cast(list[str], d.pop("on_status"))

        webhook_id = d.pop("webhook_id")

        create_job_alert_subscription_body = cls(
            plugin_id=plugin_id,
            on_status=on_status,
            webhook_id=webhook_id,
        )

        create_job_alert_subscription_body.additional_properties = d
        return create_job_alert_subscription_body

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
