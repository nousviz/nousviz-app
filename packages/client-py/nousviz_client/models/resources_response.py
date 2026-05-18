from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.index_stat import IndexStat
    from ..models.plugin_stat import PluginStat
    from ..models.postgres_summary import PostgresSummary
    from ..models.server_resources import ServerResources
    from ..models.sync_stat import SyncStat
    from ..models.table_stat import TableStat


T = TypeVar("T", bound="ResourcesResponse")


@_attrs_define
class ResourcesResponse:
    """GET /api/system/resources — all server + Postgres + per-plugin metrics in one snapshot.

    Attributes:
        collected_at (str): ISO 8601; cached 30s
        server (ServerResources): Server-level metrics. Fields are Optional because the API runs
            on Linux production but also on macOS dev (no /proc/meminfo etc.).
        postgres (PostgresSummary):
        tables (list[TableStat] | Unset): Top 50 by total size
        plugins (list[PluginStat] | Unset): Sorted by total size desc
        syncs (list[SyncStat] | Unset): Sorted by cpu_load_pct_estimate desc
        indexes_largest (list[IndexStat] | Unset): Top 20 by size
    """

    collected_at: str
    server: ServerResources
    postgres: PostgresSummary
    tables: list[TableStat] | Unset = UNSET
    plugins: list[PluginStat] | Unset = UNSET
    syncs: list[SyncStat] | Unset = UNSET
    indexes_largest: list[IndexStat] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        collected_at = self.collected_at

        server = self.server.to_dict()

        postgres = self.postgres.to_dict()

        tables: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.tables, Unset):
            tables = []
            for tables_item_data in self.tables:
                tables_item = tables_item_data.to_dict()
                tables.append(tables_item)

        plugins: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.plugins, Unset):
            plugins = []
            for plugins_item_data in self.plugins:
                plugins_item = plugins_item_data.to_dict()
                plugins.append(plugins_item)

        syncs: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.syncs, Unset):
            syncs = []
            for syncs_item_data in self.syncs:
                syncs_item = syncs_item_data.to_dict()
                syncs.append(syncs_item)

        indexes_largest: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.indexes_largest, Unset):
            indexes_largest = []
            for indexes_largest_item_data in self.indexes_largest:
                indexes_largest_item = indexes_largest_item_data.to_dict()
                indexes_largest.append(indexes_largest_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "collected_at": collected_at,
                "server": server,
                "postgres": postgres,
            }
        )
        if tables is not UNSET:
            field_dict["tables"] = tables
        if plugins is not UNSET:
            field_dict["plugins"] = plugins
        if syncs is not UNSET:
            field_dict["syncs"] = syncs
        if indexes_largest is not UNSET:
            field_dict["indexes_largest"] = indexes_largest

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.index_stat import IndexStat
        from ..models.plugin_stat import PluginStat
        from ..models.postgres_summary import PostgresSummary
        from ..models.server_resources import ServerResources
        from ..models.sync_stat import SyncStat
        from ..models.table_stat import TableStat

        d = dict(src_dict)
        collected_at = d.pop("collected_at")

        server = ServerResources.from_dict(d.pop("server"))

        postgres = PostgresSummary.from_dict(d.pop("postgres"))

        _tables = d.pop("tables", UNSET)
        tables: list[TableStat] | Unset = UNSET
        if _tables is not UNSET:
            tables = []
            for tables_item_data in _tables:
                tables_item = TableStat.from_dict(tables_item_data)

                tables.append(tables_item)

        _plugins = d.pop("plugins", UNSET)
        plugins: list[PluginStat] | Unset = UNSET
        if _plugins is not UNSET:
            plugins = []
            for plugins_item_data in _plugins:
                plugins_item = PluginStat.from_dict(plugins_item_data)

                plugins.append(plugins_item)

        _syncs = d.pop("syncs", UNSET)
        syncs: list[SyncStat] | Unset = UNSET
        if _syncs is not UNSET:
            syncs = []
            for syncs_item_data in _syncs:
                syncs_item = SyncStat.from_dict(syncs_item_data)

                syncs.append(syncs_item)

        _indexes_largest = d.pop("indexes_largest", UNSET)
        indexes_largest: list[IndexStat] | Unset = UNSET
        if _indexes_largest is not UNSET:
            indexes_largest = []
            for indexes_largest_item_data in _indexes_largest:
                indexes_largest_item = IndexStat.from_dict(indexes_largest_item_data)

                indexes_largest.append(indexes_largest_item)

        resources_response = cls(
            collected_at=collected_at,
            server=server,
            postgres=postgres,
            tables=tables,
            plugins=plugins,
            syncs=syncs,
            indexes_largest=indexes_largest,
        )

        resources_response.additional_properties = d
        return resources_response

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
