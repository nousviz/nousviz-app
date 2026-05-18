from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.history_point import HistoryPoint


T = TypeVar("T", bound="ResourcesHistoryResponse")


@_attrs_define
class ResourcesHistoryResponse:
    """GET /api/system/resources/history?metric=...&days=N.

    Attributes:
        metric (str):
        days (int):
        points (list[HistoryPoint]):
        plugin (None | str | Unset):
    """

    metric: str
    days: int
    points: list[HistoryPoint]
    plugin: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        metric = self.metric

        days = self.days

        points = []
        for points_item_data in self.points:
            points_item = points_item_data.to_dict()
            points.append(points_item)

        plugin: None | str | Unset
        if isinstance(self.plugin, Unset):
            plugin = UNSET
        else:
            plugin = self.plugin

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "metric": metric,
                "days": days,
                "points": points,
            }
        )
        if plugin is not UNSET:
            field_dict["plugin"] = plugin

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.history_point import HistoryPoint

        d = dict(src_dict)
        metric = d.pop("metric")

        days = d.pop("days")

        points = []
        _points = d.pop("points")
        for points_item_data in _points:
            points_item = HistoryPoint.from_dict(points_item_data)

            points.append(points_item)

        def _parse_plugin(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        plugin = _parse_plugin(d.pop("plugin", UNSET))

        resources_history_response = cls(
            metric=metric,
            days=days,
            points=points,
            plugin=plugin,
        )

        resources_history_response.additional_properties = d
        return resources_history_response

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
