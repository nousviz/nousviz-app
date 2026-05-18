from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alert_row_scope_filters_type_0 import AlertRowScopeFiltersType0


T = TypeVar("T", bound="AlertRow")


@_attrs_define
class AlertRow:
    """A single alert_rules row.

    extra='allow' covers any future columns and the human-readable
    `frequency_label` / `period_label` injected by `_serialize_alert`.

        Attributes:
            id (str):
            name (str):
            label (str):
            plugin_id (str):
            dataset (str):
            metric (str):
            description (None | str | Unset):
            aggregation (None | str | Unset):
            condition_type (None | str | Unset):
            threshold (float | None | Unset):
            compare_to (None | str | Unset):
            scope (None | str | Unset):
            group_by (None | str | Unset):
            scope_filters (AlertRowScopeFiltersType0 | None | Unset):
            check_frequency (None | str | Unset):
            check_period (None | str | Unset):
            cooldown_hours (int | None | Unset):
            min_baseline (float | None | Unset):
            notify_channels (list[str] | None | Unset):
            enabled (bool | None | Unset):
            is_template (bool | None | Unset):
            last_triggered (None | str | Unset):
            created_at (None | str | Unset):
            updated_at (None | str | Unset):
            frequency_label (None | str | Unset): Human-readable injection — 'Runs every hour', 'Runs once a day', etc.
            period_label (None | str | Unset):
    """

    id: str
    name: str
    label: str
    plugin_id: str
    dataset: str
    metric: str
    description: None | str | Unset = UNSET
    aggregation: None | str | Unset = UNSET
    condition_type: None | str | Unset = UNSET
    threshold: float | None | Unset = UNSET
    compare_to: None | str | Unset = UNSET
    scope: None | str | Unset = UNSET
    group_by: None | str | Unset = UNSET
    scope_filters: AlertRowScopeFiltersType0 | None | Unset = UNSET
    check_frequency: None | str | Unset = UNSET
    check_period: None | str | Unset = UNSET
    cooldown_hours: int | None | Unset = UNSET
    min_baseline: float | None | Unset = UNSET
    notify_channels: list[str] | None | Unset = UNSET
    enabled: bool | None | Unset = UNSET
    is_template: bool | None | Unset = UNSET
    last_triggered: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    frequency_label: None | str | Unset = UNSET
    period_label: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.alert_row_scope_filters_type_0 import AlertRowScopeFiltersType0

        id = self.id

        name = self.name

        label = self.label

        plugin_id = self.plugin_id

        dataset = self.dataset

        metric = self.metric

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        aggregation: None | str | Unset
        if isinstance(self.aggregation, Unset):
            aggregation = UNSET
        else:
            aggregation = self.aggregation

        condition_type: None | str | Unset
        if isinstance(self.condition_type, Unset):
            condition_type = UNSET
        else:
            condition_type = self.condition_type

        threshold: float | None | Unset
        if isinstance(self.threshold, Unset):
            threshold = UNSET
        else:
            threshold = self.threshold

        compare_to: None | str | Unset
        if isinstance(self.compare_to, Unset):
            compare_to = UNSET
        else:
            compare_to = self.compare_to

        scope: None | str | Unset
        if isinstance(self.scope, Unset):
            scope = UNSET
        else:
            scope = self.scope

        group_by: None | str | Unset
        if isinstance(self.group_by, Unset):
            group_by = UNSET
        else:
            group_by = self.group_by

        scope_filters: dict[str, Any] | None | Unset
        if isinstance(self.scope_filters, Unset):
            scope_filters = UNSET
        elif isinstance(self.scope_filters, AlertRowScopeFiltersType0):
            scope_filters = self.scope_filters.to_dict()
        else:
            scope_filters = self.scope_filters

        check_frequency: None | str | Unset
        if isinstance(self.check_frequency, Unset):
            check_frequency = UNSET
        else:
            check_frequency = self.check_frequency

        check_period: None | str | Unset
        if isinstance(self.check_period, Unset):
            check_period = UNSET
        else:
            check_period = self.check_period

        cooldown_hours: int | None | Unset
        if isinstance(self.cooldown_hours, Unset):
            cooldown_hours = UNSET
        else:
            cooldown_hours = self.cooldown_hours

        min_baseline: float | None | Unset
        if isinstance(self.min_baseline, Unset):
            min_baseline = UNSET
        else:
            min_baseline = self.min_baseline

        notify_channels: list[str] | None | Unset
        if isinstance(self.notify_channels, Unset):
            notify_channels = UNSET
        elif isinstance(self.notify_channels, list):
            notify_channels = self.notify_channels

        else:
            notify_channels = self.notify_channels

        enabled: bool | None | Unset
        if isinstance(self.enabled, Unset):
            enabled = UNSET
        else:
            enabled = self.enabled

        is_template: bool | None | Unset
        if isinstance(self.is_template, Unset):
            is_template = UNSET
        else:
            is_template = self.is_template

        last_triggered: None | str | Unset
        if isinstance(self.last_triggered, Unset):
            last_triggered = UNSET
        else:
            last_triggered = self.last_triggered

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = self.updated_at

        frequency_label: None | str | Unset
        if isinstance(self.frequency_label, Unset):
            frequency_label = UNSET
        else:
            frequency_label = self.frequency_label

        period_label: None | str | Unset
        if isinstance(self.period_label, Unset):
            period_label = UNSET
        else:
            period_label = self.period_label

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "label": label,
                "plugin_id": plugin_id,
                "dataset": dataset,
                "metric": metric,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if aggregation is not UNSET:
            field_dict["aggregation"] = aggregation
        if condition_type is not UNSET:
            field_dict["condition_type"] = condition_type
        if threshold is not UNSET:
            field_dict["threshold"] = threshold
        if compare_to is not UNSET:
            field_dict["compare_to"] = compare_to
        if scope is not UNSET:
            field_dict["scope"] = scope
        if group_by is not UNSET:
            field_dict["group_by"] = group_by
        if scope_filters is not UNSET:
            field_dict["scope_filters"] = scope_filters
        if check_frequency is not UNSET:
            field_dict["check_frequency"] = check_frequency
        if check_period is not UNSET:
            field_dict["check_period"] = check_period
        if cooldown_hours is not UNSET:
            field_dict["cooldown_hours"] = cooldown_hours
        if min_baseline is not UNSET:
            field_dict["min_baseline"] = min_baseline
        if notify_channels is not UNSET:
            field_dict["notify_channels"] = notify_channels
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if is_template is not UNSET:
            field_dict["is_template"] = is_template
        if last_triggered is not UNSET:
            field_dict["last_triggered"] = last_triggered
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if frequency_label is not UNSET:
            field_dict["frequency_label"] = frequency_label
        if period_label is not UNSET:
            field_dict["period_label"] = period_label

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alert_row_scope_filters_type_0 import AlertRowScopeFiltersType0

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        label = d.pop("label")

        plugin_id = d.pop("plugin_id")

        dataset = d.pop("dataset")

        metric = d.pop("metric")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_aggregation(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        aggregation = _parse_aggregation(d.pop("aggregation", UNSET))

        def _parse_condition_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        condition_type = _parse_condition_type(d.pop("condition_type", UNSET))

        def _parse_threshold(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        threshold = _parse_threshold(d.pop("threshold", UNSET))

        def _parse_compare_to(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        compare_to = _parse_compare_to(d.pop("compare_to", UNSET))

        def _parse_scope(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scope = _parse_scope(d.pop("scope", UNSET))

        def _parse_group_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        group_by = _parse_group_by(d.pop("group_by", UNSET))

        def _parse_scope_filters(data: object) -> AlertRowScopeFiltersType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                scope_filters_type_0 = AlertRowScopeFiltersType0.from_dict(data)

                return scope_filters_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(AlertRowScopeFiltersType0 | None | Unset, data)

        scope_filters = _parse_scope_filters(d.pop("scope_filters", UNSET))

        def _parse_check_frequency(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        check_frequency = _parse_check_frequency(d.pop("check_frequency", UNSET))

        def _parse_check_period(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        check_period = _parse_check_period(d.pop("check_period", UNSET))

        def _parse_cooldown_hours(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        cooldown_hours = _parse_cooldown_hours(d.pop("cooldown_hours", UNSET))

        def _parse_min_baseline(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        min_baseline = _parse_min_baseline(d.pop("min_baseline", UNSET))

        def _parse_notify_channels(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                notify_channels_type_0 = cast(list[str], data)

                return notify_channels_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        notify_channels = _parse_notify_channels(d.pop("notify_channels", UNSET))

        def _parse_enabled(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        enabled = _parse_enabled(d.pop("enabled", UNSET))

        def _parse_is_template(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        is_template = _parse_is_template(d.pop("is_template", UNSET))

        def _parse_last_triggered(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_triggered = _parse_last_triggered(d.pop("last_triggered", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_updated_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        def _parse_frequency_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        frequency_label = _parse_frequency_label(d.pop("frequency_label", UNSET))

        def _parse_period_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        period_label = _parse_period_label(d.pop("period_label", UNSET))

        alert_row = cls(
            id=id,
            name=name,
            label=label,
            plugin_id=plugin_id,
            dataset=dataset,
            metric=metric,
            description=description,
            aggregation=aggregation,
            condition_type=condition_type,
            threshold=threshold,
            compare_to=compare_to,
            scope=scope,
            group_by=group_by,
            scope_filters=scope_filters,
            check_frequency=check_frequency,
            check_period=check_period,
            cooldown_hours=cooldown_hours,
            min_baseline=min_baseline,
            notify_channels=notify_channels,
            enabled=enabled,
            is_template=is_template,
            last_triggered=last_triggered,
            created_at=created_at,
            updated_at=updated_at,
            frequency_label=frequency_label,
            period_label=period_label,
        )

        alert_row.additional_properties = d
        return alert_row

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
