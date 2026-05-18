from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alerts_summary import AlertsSummary
    from ..models.launchpad_response_health_snapshot_type_0 import LaunchpadResponseHealthSnapshotType0
    from ..models.launchpad_response_needs_attention_item import LaunchpadResponseNeedsAttentionItem
    from ..models.launchpad_response_recent_activity_item import LaunchpadResponseRecentActivityItem
    from ..models.launchpad_response_recent_data_changes_item import LaunchpadResponseRecentDataChangesItem
    from ..models.launchpad_response_stats import LaunchpadResponseStats


T = TypeVar("T", bound="LaunchpadResponse")


@_attrs_define
class LaunchpadResponse:
    """GET /api/launchpad — single-call data feed for the Overview page.

    Each block is best-effort populated from a separate query inside the
    handler; failures roll back the inner transaction and leave the
    block at its empty default.

        Attributes:
            recent_activity (list[LaunchpadResponseRecentActivityItem] | Unset): Up to 20 non-page-view activity events.
            recent_data_changes (list[LaunchpadResponseRecentDataChangesItem] | Unset): Per-plugin sync recency (job_runs
                success + plugin_settings._last_sync union).
            alerts_summary (AlertsSummary | Unset): Aggregate alert counts surfaced in the launchpad block.
            health_snapshot (LaunchpadResponseHealthSnapshotType0 | None | Unset):
            needs_attention (list[LaunchpadResponseNeedsAttentionItem] | Unset): System-level items needing operator action
                (e.g. expiring SSL, missing migrations).
            stats (LaunchpadResponseStats | Unset): {annotations, active_shares} aggregate counts.
    """

    recent_activity: list[LaunchpadResponseRecentActivityItem] | Unset = UNSET
    recent_data_changes: list[LaunchpadResponseRecentDataChangesItem] | Unset = UNSET
    alerts_summary: AlertsSummary | Unset = UNSET
    health_snapshot: LaunchpadResponseHealthSnapshotType0 | None | Unset = UNSET
    needs_attention: list[LaunchpadResponseNeedsAttentionItem] | Unset = UNSET
    stats: LaunchpadResponseStats | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.launchpad_response_health_snapshot_type_0 import LaunchpadResponseHealthSnapshotType0

        recent_activity: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.recent_activity, Unset):
            recent_activity = []
            for recent_activity_item_data in self.recent_activity:
                recent_activity_item = recent_activity_item_data.to_dict()
                recent_activity.append(recent_activity_item)

        recent_data_changes: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.recent_data_changes, Unset):
            recent_data_changes = []
            for recent_data_changes_item_data in self.recent_data_changes:
                recent_data_changes_item = recent_data_changes_item_data.to_dict()
                recent_data_changes.append(recent_data_changes_item)

        alerts_summary: dict[str, Any] | Unset = UNSET
        if not isinstance(self.alerts_summary, Unset):
            alerts_summary = self.alerts_summary.to_dict()

        health_snapshot: dict[str, Any] | None | Unset
        if isinstance(self.health_snapshot, Unset):
            health_snapshot = UNSET
        elif isinstance(self.health_snapshot, LaunchpadResponseHealthSnapshotType0):
            health_snapshot = self.health_snapshot.to_dict()
        else:
            health_snapshot = self.health_snapshot

        needs_attention: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.needs_attention, Unset):
            needs_attention = []
            for needs_attention_item_data in self.needs_attention:
                needs_attention_item = needs_attention_item_data.to_dict()
                needs_attention.append(needs_attention_item)

        stats: dict[str, Any] | Unset = UNSET
        if not isinstance(self.stats, Unset):
            stats = self.stats.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if recent_activity is not UNSET:
            field_dict["recent_activity"] = recent_activity
        if recent_data_changes is not UNSET:
            field_dict["recent_data_changes"] = recent_data_changes
        if alerts_summary is not UNSET:
            field_dict["alerts_summary"] = alerts_summary
        if health_snapshot is not UNSET:
            field_dict["health_snapshot"] = health_snapshot
        if needs_attention is not UNSET:
            field_dict["needs_attention"] = needs_attention
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alerts_summary import AlertsSummary
        from ..models.launchpad_response_health_snapshot_type_0 import LaunchpadResponseHealthSnapshotType0
        from ..models.launchpad_response_needs_attention_item import LaunchpadResponseNeedsAttentionItem
        from ..models.launchpad_response_recent_activity_item import LaunchpadResponseRecentActivityItem
        from ..models.launchpad_response_recent_data_changes_item import LaunchpadResponseRecentDataChangesItem
        from ..models.launchpad_response_stats import LaunchpadResponseStats

        d = dict(src_dict)
        _recent_activity = d.pop("recent_activity", UNSET)
        recent_activity: list[LaunchpadResponseRecentActivityItem] | Unset = UNSET
        if _recent_activity is not UNSET:
            recent_activity = []
            for recent_activity_item_data in _recent_activity:
                recent_activity_item = LaunchpadResponseRecentActivityItem.from_dict(recent_activity_item_data)

                recent_activity.append(recent_activity_item)

        _recent_data_changes = d.pop("recent_data_changes", UNSET)
        recent_data_changes: list[LaunchpadResponseRecentDataChangesItem] | Unset = UNSET
        if _recent_data_changes is not UNSET:
            recent_data_changes = []
            for recent_data_changes_item_data in _recent_data_changes:
                recent_data_changes_item = LaunchpadResponseRecentDataChangesItem.from_dict(
                    recent_data_changes_item_data
                )

                recent_data_changes.append(recent_data_changes_item)

        _alerts_summary = d.pop("alerts_summary", UNSET)
        alerts_summary: AlertsSummary | Unset
        if isinstance(_alerts_summary, Unset):
            alerts_summary = UNSET
        else:
            alerts_summary = AlertsSummary.from_dict(_alerts_summary)

        def _parse_health_snapshot(data: object) -> LaunchpadResponseHealthSnapshotType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                health_snapshot_type_0 = LaunchpadResponseHealthSnapshotType0.from_dict(data)

                return health_snapshot_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(LaunchpadResponseHealthSnapshotType0 | None | Unset, data)

        health_snapshot = _parse_health_snapshot(d.pop("health_snapshot", UNSET))

        _needs_attention = d.pop("needs_attention", UNSET)
        needs_attention: list[LaunchpadResponseNeedsAttentionItem] | Unset = UNSET
        if _needs_attention is not UNSET:
            needs_attention = []
            for needs_attention_item_data in _needs_attention:
                needs_attention_item = LaunchpadResponseNeedsAttentionItem.from_dict(needs_attention_item_data)

                needs_attention.append(needs_attention_item)

        _stats = d.pop("stats", UNSET)
        stats: LaunchpadResponseStats | Unset
        if isinstance(_stats, Unset):
            stats = UNSET
        else:
            stats = LaunchpadResponseStats.from_dict(_stats)

        launchpad_response = cls(
            recent_activity=recent_activity,
            recent_data_changes=recent_data_changes,
            alerts_summary=alerts_summary,
            health_snapshot=health_snapshot,
            needs_attention=needs_attention,
            stats=stats,
        )

        launchpad_response.additional_properties = d
        return launchpad_response

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
