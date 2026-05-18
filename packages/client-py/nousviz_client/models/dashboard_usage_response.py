from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.daily_activity_entry import DailyActivityEntry
    from ..models.dashboard_usage_response_action_breakdown import DashboardUsageResponseActionBreakdown
    from ..models.page_view_entry import PageViewEntry
    from ..models.plugin_activity_entry import PluginActivityEntry


T = TypeVar("T", bound="DashboardUsageResponse")


@_attrs_define
class DashboardUsageResponse:
    """GET /api/activity/dashboard-usage — analytics aggregate.

    `unused_dashboards` enumerates manifest-declared dashboard paths
    that received zero page_view events in the period.

        Attributes:
            period_days (int):
            total_events (int):
            page_views (list[PageViewEntry]):
            plugin_activity (list[PluginActivityEntry]):
            action_breakdown (DashboardUsageResponseActionBreakdown):
            daily_activity (list[DailyActivityEntry]):
            unused_dashboards (list[str]):
    """

    period_days: int
    total_events: int
    page_views: list[PageViewEntry]
    plugin_activity: list[PluginActivityEntry]
    action_breakdown: DashboardUsageResponseActionBreakdown
    daily_activity: list[DailyActivityEntry]
    unused_dashboards: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        period_days = self.period_days

        total_events = self.total_events

        page_views = []
        for page_views_item_data in self.page_views:
            page_views_item = page_views_item_data.to_dict()
            page_views.append(page_views_item)

        plugin_activity = []
        for plugin_activity_item_data in self.plugin_activity:
            plugin_activity_item = plugin_activity_item_data.to_dict()
            plugin_activity.append(plugin_activity_item)

        action_breakdown = self.action_breakdown.to_dict()

        daily_activity = []
        for daily_activity_item_data in self.daily_activity:
            daily_activity_item = daily_activity_item_data.to_dict()
            daily_activity.append(daily_activity_item)

        unused_dashboards = self.unused_dashboards

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "period_days": period_days,
                "total_events": total_events,
                "page_views": page_views,
                "plugin_activity": plugin_activity,
                "action_breakdown": action_breakdown,
                "daily_activity": daily_activity,
                "unused_dashboards": unused_dashboards,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.daily_activity_entry import DailyActivityEntry
        from ..models.dashboard_usage_response_action_breakdown import DashboardUsageResponseActionBreakdown
        from ..models.page_view_entry import PageViewEntry
        from ..models.plugin_activity_entry import PluginActivityEntry

        d = dict(src_dict)
        period_days = d.pop("period_days")

        total_events = d.pop("total_events")

        page_views = []
        _page_views = d.pop("page_views")
        for page_views_item_data in _page_views:
            page_views_item = PageViewEntry.from_dict(page_views_item_data)

            page_views.append(page_views_item)

        plugin_activity = []
        _plugin_activity = d.pop("plugin_activity")
        for plugin_activity_item_data in _plugin_activity:
            plugin_activity_item = PluginActivityEntry.from_dict(plugin_activity_item_data)

            plugin_activity.append(plugin_activity_item)

        action_breakdown = DashboardUsageResponseActionBreakdown.from_dict(d.pop("action_breakdown"))

        daily_activity = []
        _daily_activity = d.pop("daily_activity")
        for daily_activity_item_data in _daily_activity:
            daily_activity_item = DailyActivityEntry.from_dict(daily_activity_item_data)

            daily_activity.append(daily_activity_item)

        unused_dashboards = cast(list[str], d.pop("unused_dashboards"))

        dashboard_usage_response = cls(
            period_days=period_days,
            total_events=total_events,
            page_views=page_views,
            plugin_activity=plugin_activity,
            action_breakdown=action_breakdown,
            daily_activity=daily_activity,
            unused_dashboards=unused_dashboards,
        )

        dashboard_usage_response.additional_properties = d
        return dashboard_usage_response

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
