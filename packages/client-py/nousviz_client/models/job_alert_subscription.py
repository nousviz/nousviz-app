from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JobAlertSubscription")


@_attrs_define
class JobAlertSubscription:
    """One row in the job_alert_subscriptions table joined with the
    referenced webhook's display info. webhook_name / webhook_url are
    null when the webhooks plugin is uninstalled (orphan subscription).

        Attributes:
            id (str):
            plugin_id (str): '*' for any plugin, or a specific plugin slug.
            on_status (list[str]): Terminal statuses this subscription fires on (subset of error/timeout/cancelled).
            webhook_id (str):
            enabled (bool):
            webhook_name (None | str | Unset):
            webhook_url (None | str | Unset):
            webhook_active (bool | Unset):  Default: False.
            webhook_channel_type (None | str | Unset): Channel type of the referenced webhook (generic/slack/discord/teams).
                Null when the webhooks plugin is uninstalled (orphan subscription).
            updated_at (None | str | Unset):
    """

    id: str
    plugin_id: str
    on_status: list[str]
    webhook_id: str
    enabled: bool
    webhook_name: None | str | Unset = UNSET
    webhook_url: None | str | Unset = UNSET
    webhook_active: bool | Unset = False
    webhook_channel_type: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        plugin_id = self.plugin_id

        on_status = self.on_status

        webhook_id = self.webhook_id

        enabled = self.enabled

        webhook_name: None | str | Unset
        if isinstance(self.webhook_name, Unset):
            webhook_name = UNSET
        else:
            webhook_name = self.webhook_name

        webhook_url: None | str | Unset
        if isinstance(self.webhook_url, Unset):
            webhook_url = UNSET
        else:
            webhook_url = self.webhook_url

        webhook_active = self.webhook_active

        webhook_channel_type: None | str | Unset
        if isinstance(self.webhook_channel_type, Unset):
            webhook_channel_type = UNSET
        else:
            webhook_channel_type = self.webhook_channel_type

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "plugin_id": plugin_id,
                "on_status": on_status,
                "webhook_id": webhook_id,
                "enabled": enabled,
            }
        )
        if webhook_name is not UNSET:
            field_dict["webhook_name"] = webhook_name
        if webhook_url is not UNSET:
            field_dict["webhook_url"] = webhook_url
        if webhook_active is not UNSET:
            field_dict["webhook_active"] = webhook_active
        if webhook_channel_type is not UNSET:
            field_dict["webhook_channel_type"] = webhook_channel_type
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        plugin_id = d.pop("plugin_id")

        on_status = cast(list[str], d.pop("on_status"))

        webhook_id = d.pop("webhook_id")

        enabled = d.pop("enabled")

        def _parse_webhook_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        webhook_name = _parse_webhook_name(d.pop("webhook_name", UNSET))

        def _parse_webhook_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        webhook_url = _parse_webhook_url(d.pop("webhook_url", UNSET))

        webhook_active = d.pop("webhook_active", UNSET)

        def _parse_webhook_channel_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        webhook_channel_type = _parse_webhook_channel_type(d.pop("webhook_channel_type", UNSET))

        def _parse_updated_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        job_alert_subscription = cls(
            id=id,
            plugin_id=plugin_id,
            on_status=on_status,
            webhook_id=webhook_id,
            enabled=enabled,
            webhook_name=webhook_name,
            webhook_url=webhook_url,
            webhook_active=webhook_active,
            webhook_channel_type=webhook_channel_type,
            updated_at=updated_at,
        )

        job_alert_subscription.additional_properties = d
        return job_alert_subscription

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
