from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alert_update_scope_filters_type_0 import AlertUpdateScopeFiltersType0


T = TypeVar("T", bound="AlertUpdate")


@_attrs_define
class AlertUpdate:
    """
    Attributes:
        label (None | str | Unset):
        description (None | str | Unset):
        enabled (bool | None | Unset):
        threshold (float | None | Unset):
        compare_to (None | str | Unset):
        check_period (None | str | Unset):
        group_by (None | str | Unset):
        scope_filters (AlertUpdateScopeFiltersType0 | None | Unset):
        cooldown_hours (int | None | Unset):
        min_baseline (float | None | Unset):
        notify_channels (list[str] | None | Unset):
    """

    label: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    enabled: bool | None | Unset = UNSET
    threshold: float | None | Unset = UNSET
    compare_to: None | str | Unset = UNSET
    check_period: None | str | Unset = UNSET
    group_by: None | str | Unset = UNSET
    scope_filters: AlertUpdateScopeFiltersType0 | None | Unset = UNSET
    cooldown_hours: int | None | Unset = UNSET
    min_baseline: float | None | Unset = UNSET
    notify_channels: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.alert_update_scope_filters_type_0 import AlertUpdateScopeFiltersType0

        label: None | str | Unset
        if isinstance(self.label, Unset):
            label = UNSET
        else:
            label = self.label

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        enabled: bool | None | Unset
        if isinstance(self.enabled, Unset):
            enabled = UNSET
        else:
            enabled = self.enabled

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

        check_period: None | str | Unset
        if isinstance(self.check_period, Unset):
            check_period = UNSET
        else:
            check_period = self.check_period

        group_by: None | str | Unset
        if isinstance(self.group_by, Unset):
            group_by = UNSET
        else:
            group_by = self.group_by

        scope_filters: dict[str, Any] | None | Unset
        if isinstance(self.scope_filters, Unset):
            scope_filters = UNSET
        elif isinstance(self.scope_filters, AlertUpdateScopeFiltersType0):
            scope_filters = self.scope_filters.to_dict()
        else:
            scope_filters = self.scope_filters

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

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if label is not UNSET:
            field_dict["label"] = label
        if description is not UNSET:
            field_dict["description"] = description
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if threshold is not UNSET:
            field_dict["threshold"] = threshold
        if compare_to is not UNSET:
            field_dict["compare_to"] = compare_to
        if check_period is not UNSET:
            field_dict["check_period"] = check_period
        if group_by is not UNSET:
            field_dict["group_by"] = group_by
        if scope_filters is not UNSET:
            field_dict["scope_filters"] = scope_filters
        if cooldown_hours is not UNSET:
            field_dict["cooldown_hours"] = cooldown_hours
        if min_baseline is not UNSET:
            field_dict["min_baseline"] = min_baseline
        if notify_channels is not UNSET:
            field_dict["notify_channels"] = notify_channels

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alert_update_scope_filters_type_0 import AlertUpdateScopeFiltersType0

        d = dict(src_dict)

        def _parse_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        label = _parse_label(d.pop("label", UNSET))

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_enabled(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        enabled = _parse_enabled(d.pop("enabled", UNSET))

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

        def _parse_check_period(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        check_period = _parse_check_period(d.pop("check_period", UNSET))

        def _parse_group_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        group_by = _parse_group_by(d.pop("group_by", UNSET))

        def _parse_scope_filters(data: object) -> AlertUpdateScopeFiltersType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                scope_filters_type_0 = AlertUpdateScopeFiltersType0.from_dict(data)

                return scope_filters_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(AlertUpdateScopeFiltersType0 | None | Unset, data)

        scope_filters = _parse_scope_filters(d.pop("scope_filters", UNSET))

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

        alert_update = cls(
            label=label,
            description=description,
            enabled=enabled,
            threshold=threshold,
            compare_to=compare_to,
            check_period=check_period,
            group_by=group_by,
            scope_filters=scope_filters,
            cooldown_hours=cooldown_hours,
            min_baseline=min_baseline,
            notify_channels=notify_channels,
        )

        alert_update.additional_properties = d
        return alert_update

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
