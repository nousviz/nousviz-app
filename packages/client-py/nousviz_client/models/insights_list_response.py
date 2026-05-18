from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.insight_entry import InsightEntry


T = TypeVar("T", bound="InsightsListResponse")


@_attrs_define
class InsightsListResponse:
    """GET /api/insights — aggregated insights from all installed plugins.

    Sorted by severity (critical → warning → info → good → tip), then
    truncated to `limit`. `total` is the un-truncated count.

        Attributes:
            insights (list[InsightEntry]):
            total (int):
    """

    insights: list[InsightEntry]
    total: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        insights = []
        for insights_item_data in self.insights:
            insights_item = insights_item_data.to_dict()
            insights.append(insights_item)

        total = self.total

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "insights": insights,
                "total": total,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.insight_entry import InsightEntry

        d = dict(src_dict)
        insights = []
        _insights = d.pop("insights")
        for insights_item_data in _insights:
            insights_item = InsightEntry.from_dict(insights_item_data)

            insights.append(insights_item)

        total = d.pop("total")

        insights_list_response = cls(
            insights=insights,
            total=total,
        )

        insights_list_response.additional_properties = d
        return insights_list_response

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
