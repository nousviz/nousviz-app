from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="StatsBlock")


@_attrs_define
class StatsBlock:
    """Aggregate counts surfaced in /health for the operator dashboard.

    Attributes:
        active_alerts (int): Count of currently-firing alerts.
        fusions (int): Count of configured fusions.
        annotations (int): Count of operator annotations.
        installed_plugins (int): Count of plugins installed locally.
        plugin_tables (int): Count of plugin-managed tables in Postgres.
        active_shares (int): Count of non-revoked shared links.
    """

    active_alerts: int
    fusions: int
    annotations: int
    installed_plugins: int
    plugin_tables: int
    active_shares: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        active_alerts = self.active_alerts

        fusions = self.fusions

        annotations = self.annotations

        installed_plugins = self.installed_plugins

        plugin_tables = self.plugin_tables

        active_shares = self.active_shares

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "active_alerts": active_alerts,
                "fusions": fusions,
                "annotations": annotations,
                "installed_plugins": installed_plugins,
                "plugin_tables": plugin_tables,
                "active_shares": active_shares,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        active_alerts = d.pop("active_alerts")

        fusions = d.pop("fusions")

        annotations = d.pop("annotations")

        installed_plugins = d.pop("installed_plugins")

        plugin_tables = d.pop("plugin_tables")

        active_shares = d.pop("active_shares")

        stats_block = cls(
            active_alerts=active_alerts,
            fusions=fusions,
            annotations=annotations,
            installed_plugins=installed_plugins,
            plugin_tables=plugin_tables,
            active_shares=active_shares,
        )

        stats_block.additional_properties = d
        return stats_block

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
