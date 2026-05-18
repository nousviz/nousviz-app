from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alerts_summary_recent_triggers_item import AlertsSummaryRecentTriggersItem


T = TypeVar("T", bound="AlertsSummary")


@_attrs_define
class AlertsSummary:
    """Aggregate alert counts surfaced in the launchpad block.

    Attributes:
        total (int | Unset):  Default: 0.
        enabled (int | Unset):  Default: 0.
        triggered_24h (int | Unset):  Default: 0.
        recent_triggers (list[AlertsSummaryRecentTriggersItem] | Unset): Recent alert_events rows; row shape varies by
            alert type.
    """

    total: int | Unset = 0
    enabled: int | Unset = 0
    triggered_24h: int | Unset = 0
    recent_triggers: list[AlertsSummaryRecentTriggersItem] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        total = self.total

        enabled = self.enabled

        triggered_24h = self.triggered_24h

        recent_triggers: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.recent_triggers, Unset):
            recent_triggers = []
            for recent_triggers_item_data in self.recent_triggers:
                recent_triggers_item = recent_triggers_item_data.to_dict()
                recent_triggers.append(recent_triggers_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if total is not UNSET:
            field_dict["total"] = total
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if triggered_24h is not UNSET:
            field_dict["triggered_24h"] = triggered_24h
        if recent_triggers is not UNSET:
            field_dict["recent_triggers"] = recent_triggers

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alerts_summary_recent_triggers_item import AlertsSummaryRecentTriggersItem

        d = dict(src_dict)
        total = d.pop("total", UNSET)

        enabled = d.pop("enabled", UNSET)

        triggered_24h = d.pop("triggered_24h", UNSET)

        _recent_triggers = d.pop("recent_triggers", UNSET)
        recent_triggers: list[AlertsSummaryRecentTriggersItem] | Unset = UNSET
        if _recent_triggers is not UNSET:
            recent_triggers = []
            for recent_triggers_item_data in _recent_triggers:
                recent_triggers_item = AlertsSummaryRecentTriggersItem.from_dict(recent_triggers_item_data)

                recent_triggers.append(recent_triggers_item)

        alerts_summary = cls(
            total=total,
            enabled=enabled,
            triggered_24h=triggered_24h,
            recent_triggers=recent_triggers,
        )

        alerts_summary.additional_properties = d
        return alerts_summary

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
