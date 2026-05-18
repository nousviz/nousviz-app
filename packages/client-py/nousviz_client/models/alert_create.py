from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alert_create_scope_filters import AlertCreateScopeFilters


T = TypeVar("T", bound="AlertCreate")


@_attrs_define
class AlertCreate:
    """
    Attributes:
        name (str):
        label (str):
        plugin_id (str):
        dataset (str):
        metric (str):
        description (None | str | Unset):
        aggregation (str | Unset):  Default: 'sum'.
        condition_type (str | Unset):  Default: 'threshold_drop'.
        threshold (float | None | Unset):
        compare_to (str | Unset):  Default: '7d_avg'.
        scope (str | Unset):  Default: 'all'.
        group_by (None | str | Unset):
        scope_filters (AlertCreateScopeFilters | Unset):
        check_frequency (str | Unset):  Default: 'daily'.
        check_period (str | Unset):  Default: 'yesterday'.
        cooldown_hours (int | Unset):  Default: 24.
        min_baseline (float | Unset):  Default: 0.0.
        notify_channels (list[str] | Unset):
        enabled (bool | Unset):  Default: True.
        is_template (bool | Unset):  Default: False.
    """

    name: str
    label: str
    plugin_id: str
    dataset: str
    metric: str
    description: None | str | Unset = UNSET
    aggregation: str | Unset = "sum"
    condition_type: str | Unset = "threshold_drop"
    threshold: float | None | Unset = UNSET
    compare_to: str | Unset = "7d_avg"
    scope: str | Unset = "all"
    group_by: None | str | Unset = UNSET
    scope_filters: AlertCreateScopeFilters | Unset = UNSET
    check_frequency: str | Unset = "daily"
    check_period: str | Unset = "yesterday"
    cooldown_hours: int | Unset = 24
    min_baseline: float | Unset = 0.0
    notify_channels: list[str] | Unset = UNSET
    enabled: bool | Unset = True
    is_template: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
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

        aggregation = self.aggregation

        condition_type = self.condition_type

        threshold: float | None | Unset
        if isinstance(self.threshold, Unset):
            threshold = UNSET
        else:
            threshold = self.threshold

        compare_to = self.compare_to

        scope = self.scope

        group_by: None | str | Unset
        if isinstance(self.group_by, Unset):
            group_by = UNSET
        else:
            group_by = self.group_by

        scope_filters: dict[str, Any] | Unset = UNSET
        if not isinstance(self.scope_filters, Unset):
            scope_filters = self.scope_filters.to_dict()

        check_frequency = self.check_frequency

        check_period = self.check_period

        cooldown_hours = self.cooldown_hours

        min_baseline = self.min_baseline

        notify_channels: list[str] | Unset = UNSET
        if not isinstance(self.notify_channels, Unset):
            notify_channels = self.notify_channels

        enabled = self.enabled

        is_template = self.is_template

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
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

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alert_create_scope_filters import AlertCreateScopeFilters

        d = dict(src_dict)
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

        aggregation = d.pop("aggregation", UNSET)

        condition_type = d.pop("condition_type", UNSET)

        def _parse_threshold(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        threshold = _parse_threshold(d.pop("threshold", UNSET))

        compare_to = d.pop("compare_to", UNSET)

        scope = d.pop("scope", UNSET)

        def _parse_group_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        group_by = _parse_group_by(d.pop("group_by", UNSET))

        _scope_filters = d.pop("scope_filters", UNSET)
        scope_filters: AlertCreateScopeFilters | Unset
        if isinstance(_scope_filters, Unset):
            scope_filters = UNSET
        else:
            scope_filters = AlertCreateScopeFilters.from_dict(_scope_filters)

        check_frequency = d.pop("check_frequency", UNSET)

        check_period = d.pop("check_period", UNSET)

        cooldown_hours = d.pop("cooldown_hours", UNSET)

        min_baseline = d.pop("min_baseline", UNSET)

        notify_channels = cast(list[str], d.pop("notify_channels", UNSET))

        enabled = d.pop("enabled", UNSET)

        is_template = d.pop("is_template", UNSET)

        alert_create = cls(
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
        )

        alert_create.additional_properties = d
        return alert_create

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
