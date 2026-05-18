from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alert_sparkline_day import AlertSparklineDay
    from ..models.alert_sparkline_response_semantic_summary import AlertSparklineResponseSemanticSummary


T = TypeVar("T", bound="AlertSparklineResponse")


@_attrs_define
class AlertSparklineResponse:
    """GET /api/alerts/{alert_id}/sparkline — last N days of trigger activity.

    Attributes:
        alert_id (str):
        alert_label (str):
        days (list[AlertSparklineDay]):
        total_triggers (int):
        semantic_summary (AlertSparklineResponseSemanticSummary): Counts keyed by 'useful' | 'neutral' | 'useless'.
        check_frequency (None | str | Unset):
        frequency_label (None | str | Unset):
        check_period (None | str | Unset):
        period_label (None | str | Unset):
        cooldown_hours (int | None | Unset):
    """

    alert_id: str
    alert_label: str
    days: list[AlertSparklineDay]
    total_triggers: int
    semantic_summary: AlertSparklineResponseSemanticSummary
    check_frequency: None | str | Unset = UNSET
    frequency_label: None | str | Unset = UNSET
    check_period: None | str | Unset = UNSET
    period_label: None | str | Unset = UNSET
    cooldown_hours: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        alert_id = self.alert_id

        alert_label = self.alert_label

        days = []
        for days_item_data in self.days:
            days_item = days_item_data.to_dict()
            days.append(days_item)

        total_triggers = self.total_triggers

        semantic_summary = self.semantic_summary.to_dict()

        check_frequency: None | str | Unset
        if isinstance(self.check_frequency, Unset):
            check_frequency = UNSET
        else:
            check_frequency = self.check_frequency

        frequency_label: None | str | Unset
        if isinstance(self.frequency_label, Unset):
            frequency_label = UNSET
        else:
            frequency_label = self.frequency_label

        check_period: None | str | Unset
        if isinstance(self.check_period, Unset):
            check_period = UNSET
        else:
            check_period = self.check_period

        period_label: None | str | Unset
        if isinstance(self.period_label, Unset):
            period_label = UNSET
        else:
            period_label = self.period_label

        cooldown_hours: int | None | Unset
        if isinstance(self.cooldown_hours, Unset):
            cooldown_hours = UNSET
        else:
            cooldown_hours = self.cooldown_hours

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "alert_id": alert_id,
                "alert_label": alert_label,
                "days": days,
                "total_triggers": total_triggers,
                "semantic_summary": semantic_summary,
            }
        )
        if check_frequency is not UNSET:
            field_dict["check_frequency"] = check_frequency
        if frequency_label is not UNSET:
            field_dict["frequency_label"] = frequency_label
        if check_period is not UNSET:
            field_dict["check_period"] = check_period
        if period_label is not UNSET:
            field_dict["period_label"] = period_label
        if cooldown_hours is not UNSET:
            field_dict["cooldown_hours"] = cooldown_hours

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alert_sparkline_day import AlertSparklineDay
        from ..models.alert_sparkline_response_semantic_summary import AlertSparklineResponseSemanticSummary

        d = dict(src_dict)
        alert_id = d.pop("alert_id")

        alert_label = d.pop("alert_label")

        days = []
        _days = d.pop("days")
        for days_item_data in _days:
            days_item = AlertSparklineDay.from_dict(days_item_data)

            days.append(days_item)

        total_triggers = d.pop("total_triggers")

        semantic_summary = AlertSparklineResponseSemanticSummary.from_dict(d.pop("semantic_summary"))

        def _parse_check_frequency(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        check_frequency = _parse_check_frequency(d.pop("check_frequency", UNSET))

        def _parse_frequency_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        frequency_label = _parse_frequency_label(d.pop("frequency_label", UNSET))

        def _parse_check_period(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        check_period = _parse_check_period(d.pop("check_period", UNSET))

        def _parse_period_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        period_label = _parse_period_label(d.pop("period_label", UNSET))

        def _parse_cooldown_hours(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        cooldown_hours = _parse_cooldown_hours(d.pop("cooldown_hours", UNSET))

        alert_sparkline_response = cls(
            alert_id=alert_id,
            alert_label=alert_label,
            days=days,
            total_triggers=total_triggers,
            semantic_summary=semantic_summary,
            check_frequency=check_frequency,
            frequency_label=frequency_label,
            check_period=check_period,
            period_label=period_label,
            cooldown_hours=cooldown_hours,
        )

        alert_sparkline_response.additional_properties = d
        return alert_sparkline_response

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
