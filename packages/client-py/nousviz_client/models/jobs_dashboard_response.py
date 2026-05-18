from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.jobs_dashboard_failing_item import JobsDashboardFailingItem
    from ..models.jobs_dashboard_now_item import JobsDashboardNowItem
    from ..models.jobs_dashboard_recent_item import JobsDashboardRecentItem
    from ..models.jobs_dashboard_upcoming_item import JobsDashboardUpcomingItem


T = TypeVar("T", bound="JobsDashboardResponse")


@_attrs_define
class JobsDashboardResponse:
    """B277: GET /api/jobs/dashboard — 4-section centralized job state.

    Each section is independently sized, so callers can render whichever
    blocks have content. `collected_at` lets the client tell when a
    cached vs fresh snapshot is being shown.

        Attributes:
            collected_at (str):
            now (list[JobsDashboardNowItem]):
            recent (list[JobsDashboardRecentItem]):
            upcoming (list[JobsDashboardUpcomingItem]):
            failing (list[JobsDashboardFailingItem]):
    """

    collected_at: str
    now: list[JobsDashboardNowItem]
    recent: list[JobsDashboardRecentItem]
    upcoming: list[JobsDashboardUpcomingItem]
    failing: list[JobsDashboardFailingItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        collected_at = self.collected_at

        now = []
        for now_item_data in self.now:
            now_item = now_item_data.to_dict()
            now.append(now_item)

        recent = []
        for recent_item_data in self.recent:
            recent_item = recent_item_data.to_dict()
            recent.append(recent_item)

        upcoming = []
        for upcoming_item_data in self.upcoming:
            upcoming_item = upcoming_item_data.to_dict()
            upcoming.append(upcoming_item)

        failing = []
        for failing_item_data in self.failing:
            failing_item = failing_item_data.to_dict()
            failing.append(failing_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "collected_at": collected_at,
                "now": now,
                "recent": recent,
                "upcoming": upcoming,
                "failing": failing,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.jobs_dashboard_failing_item import JobsDashboardFailingItem
        from ..models.jobs_dashboard_now_item import JobsDashboardNowItem
        from ..models.jobs_dashboard_recent_item import JobsDashboardRecentItem
        from ..models.jobs_dashboard_upcoming_item import JobsDashboardUpcomingItem

        d = dict(src_dict)
        collected_at = d.pop("collected_at")

        now = []
        _now = d.pop("now")
        for now_item_data in _now:
            now_item = JobsDashboardNowItem.from_dict(now_item_data)

            now.append(now_item)

        recent = []
        _recent = d.pop("recent")
        for recent_item_data in _recent:
            recent_item = JobsDashboardRecentItem.from_dict(recent_item_data)

            recent.append(recent_item)

        upcoming = []
        _upcoming = d.pop("upcoming")
        for upcoming_item_data in _upcoming:
            upcoming_item = JobsDashboardUpcomingItem.from_dict(upcoming_item_data)

            upcoming.append(upcoming_item)

        failing = []
        _failing = d.pop("failing")
        for failing_item_data in _failing:
            failing_item = JobsDashboardFailingItem.from_dict(failing_item_data)

            failing.append(failing_item)

        jobs_dashboard_response = cls(
            collected_at=collected_at,
            now=now,
            recent=recent,
            upcoming=upcoming,
            failing=failing,
        )

        jobs_dashboard_response.additional_properties = d
        return jobs_dashboard_response

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
