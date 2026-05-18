from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.time_per_page_entry import TimePerPageEntry
    from ..models.user_analytics_response_browsers import UserAnalyticsResponseBrowsers
    from ..models.user_analytics_response_devices import UserAnalyticsResponseDevices
    from ..models.user_analytics_response_hourly_distribution import UserAnalyticsResponseHourlyDistribution
    from ..models.user_analytics_response_ip_activity import UserAnalyticsResponseIpActivity


T = TypeVar("T", bound="UserAnalyticsResponse")


@_attrs_define
class UserAnalyticsResponse:
    """GET /api/activity/analytics — admin analytics overview.

    `devices`, `browsers`, `ip_activity`, `hourly_distribution` are
    histogram-style maps keyed by the categorical value; treated as
    open-ended dicts since the keys are inferred from user-agent / IP /
    timestamp parsing.

        Attributes:
            period_days (int):
            total_events (int):
            total_page_views (int):
            estimated_time_minutes (float):
            estimated_time_display (str):
            sessions (int):
            avg_session_minutes (float):
            devices (UserAnalyticsResponseDevices):
            browsers (UserAnalyticsResponseBrowsers):
            unique_ips (list[str]):
            ip_activity (UserAnalyticsResponseIpActivity):
            peak_hour (str):
            hourly_distribution (UserAnalyticsResponseHourlyDistribution):
            time_per_page (list[TimePerPageEntry]):
    """

    period_days: int
    total_events: int
    total_page_views: int
    estimated_time_minutes: float
    estimated_time_display: str
    sessions: int
    avg_session_minutes: float
    devices: UserAnalyticsResponseDevices
    browsers: UserAnalyticsResponseBrowsers
    unique_ips: list[str]
    ip_activity: UserAnalyticsResponseIpActivity
    peak_hour: str
    hourly_distribution: UserAnalyticsResponseHourlyDistribution
    time_per_page: list[TimePerPageEntry]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        period_days = self.period_days

        total_events = self.total_events

        total_page_views = self.total_page_views

        estimated_time_minutes = self.estimated_time_minutes

        estimated_time_display = self.estimated_time_display

        sessions = self.sessions

        avg_session_minutes = self.avg_session_minutes

        devices = self.devices.to_dict()

        browsers = self.browsers.to_dict()

        unique_ips = self.unique_ips

        ip_activity = self.ip_activity.to_dict()

        peak_hour = self.peak_hour

        hourly_distribution = self.hourly_distribution.to_dict()

        time_per_page = []
        for time_per_page_item_data in self.time_per_page:
            time_per_page_item = time_per_page_item_data.to_dict()
            time_per_page.append(time_per_page_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "period_days": period_days,
                "total_events": total_events,
                "total_page_views": total_page_views,
                "estimated_time_minutes": estimated_time_minutes,
                "estimated_time_display": estimated_time_display,
                "sessions": sessions,
                "avg_session_minutes": avg_session_minutes,
                "devices": devices,
                "browsers": browsers,
                "unique_ips": unique_ips,
                "ip_activity": ip_activity,
                "peak_hour": peak_hour,
                "hourly_distribution": hourly_distribution,
                "time_per_page": time_per_page,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.time_per_page_entry import TimePerPageEntry
        from ..models.user_analytics_response_browsers import UserAnalyticsResponseBrowsers
        from ..models.user_analytics_response_devices import UserAnalyticsResponseDevices
        from ..models.user_analytics_response_hourly_distribution import UserAnalyticsResponseHourlyDistribution
        from ..models.user_analytics_response_ip_activity import UserAnalyticsResponseIpActivity

        d = dict(src_dict)
        period_days = d.pop("period_days")

        total_events = d.pop("total_events")

        total_page_views = d.pop("total_page_views")

        estimated_time_minutes = d.pop("estimated_time_minutes")

        estimated_time_display = d.pop("estimated_time_display")

        sessions = d.pop("sessions")

        avg_session_minutes = d.pop("avg_session_minutes")

        devices = UserAnalyticsResponseDevices.from_dict(d.pop("devices"))

        browsers = UserAnalyticsResponseBrowsers.from_dict(d.pop("browsers"))

        unique_ips = cast(list[str], d.pop("unique_ips"))

        ip_activity = UserAnalyticsResponseIpActivity.from_dict(d.pop("ip_activity"))

        peak_hour = d.pop("peak_hour")

        hourly_distribution = UserAnalyticsResponseHourlyDistribution.from_dict(d.pop("hourly_distribution"))

        time_per_page = []
        _time_per_page = d.pop("time_per_page")
        for time_per_page_item_data in _time_per_page:
            time_per_page_item = TimePerPageEntry.from_dict(time_per_page_item_data)

            time_per_page.append(time_per_page_item)

        user_analytics_response = cls(
            period_days=period_days,
            total_events=total_events,
            total_page_views=total_page_views,
            estimated_time_minutes=estimated_time_minutes,
            estimated_time_display=estimated_time_display,
            sessions=sessions,
            avg_session_minutes=avg_session_minutes,
            devices=devices,
            browsers=browsers,
            unique_ips=unique_ips,
            ip_activity=ip_activity,
            peak_hour=peak_hour,
            hourly_distribution=hourly_distribution,
            time_per_page=time_per_page,
        )

        user_analytics_response.additional_properties = d
        return user_analytics_response

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
