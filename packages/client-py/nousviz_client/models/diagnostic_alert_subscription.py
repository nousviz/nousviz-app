from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DiagnosticAlertSubscription")


@_attrs_define
class DiagnosticAlertSubscription:
    """One outbound webhook + its diagnostic-alert subscription state.

    v0.9.11.24 (B283) renamed `webhook_slug` → `webhook_id` and added
    `channel_type`. Existing slug-keyed subscriptions were backfilled
    by migration 070; the API now exposes the UUID directly.

        Attributes:
            webhook_id (str): webhook_endpoints.id (UUID).
            name (str):
            is_active (bool):
            subscribed (bool): True iff the operator has explicitly subscribed this webhook to diagnostic alerts.
            url (None | str | Unset):
            channel_type (str | Unset): Channel type from webhook_endpoints: generic / slack / discord / teams. Default:
                'generic'.
            updated_at (None | str | Unset):
    """

    webhook_id: str
    name: str
    is_active: bool
    subscribed: bool
    url: None | str | Unset = UNSET
    channel_type: str | Unset = "generic"
    updated_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        webhook_id = self.webhook_id

        name = self.name

        is_active = self.is_active

        subscribed = self.subscribed

        url: None | str | Unset
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url

        channel_type = self.channel_type

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "webhook_id": webhook_id,
                "name": name,
                "is_active": is_active,
                "subscribed": subscribed,
            }
        )
        if url is not UNSET:
            field_dict["url"] = url
        if channel_type is not UNSET:
            field_dict["channel_type"] = channel_type
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        webhook_id = d.pop("webhook_id")

        name = d.pop("name")

        is_active = d.pop("is_active")

        subscribed = d.pop("subscribed")

        def _parse_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        url = _parse_url(d.pop("url", UNSET))

        channel_type = d.pop("channel_type", UNSET)

        def _parse_updated_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        diagnostic_alert_subscription = cls(
            webhook_id=webhook_id,
            name=name,
            is_active=is_active,
            subscribed=subscribed,
            url=url,
            channel_type=channel_type,
            updated_at=updated_at,
        )

        diagnostic_alert_subscription.additional_properties = d
        return diagnostic_alert_subscription

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
