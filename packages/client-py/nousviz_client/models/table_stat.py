from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TableStat")


@_attrs_define
class TableStat:
    """
    Attributes:
        schema (str):
        name (str):
        total_size_mb (float):
        data_mb (float):
        index_mb (float):
        rows (int):
        dead_rows (int):
        dead_pct (float):
        seq_scan_count (int):
        idx_scan_count (int):
        seq_scan_pct (float):
        plugin (None | str | Unset): Plugin slug, or null for host-owned tables
        last_vacuum (None | str | Unset):
        last_analyze (None | str | Unset):
    """

    schema: str
    name: str
    total_size_mb: float
    data_mb: float
    index_mb: float
    rows: int
    dead_rows: int
    dead_pct: float
    seq_scan_count: int
    idx_scan_count: int
    seq_scan_pct: float
    plugin: None | str | Unset = UNSET
    last_vacuum: None | str | Unset = UNSET
    last_analyze: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        schema = self.schema

        name = self.name

        total_size_mb = self.total_size_mb

        data_mb = self.data_mb

        index_mb = self.index_mb

        rows = self.rows

        dead_rows = self.dead_rows

        dead_pct = self.dead_pct

        seq_scan_count = self.seq_scan_count

        idx_scan_count = self.idx_scan_count

        seq_scan_pct = self.seq_scan_pct

        plugin: None | str | Unset
        if isinstance(self.plugin, Unset):
            plugin = UNSET
        else:
            plugin = self.plugin

        last_vacuum: None | str | Unset
        if isinstance(self.last_vacuum, Unset):
            last_vacuum = UNSET
        else:
            last_vacuum = self.last_vacuum

        last_analyze: None | str | Unset
        if isinstance(self.last_analyze, Unset):
            last_analyze = UNSET
        else:
            last_analyze = self.last_analyze

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "schema": schema,
                "name": name,
                "total_size_mb": total_size_mb,
                "data_mb": data_mb,
                "index_mb": index_mb,
                "rows": rows,
                "dead_rows": dead_rows,
                "dead_pct": dead_pct,
                "seq_scan_count": seq_scan_count,
                "idx_scan_count": idx_scan_count,
                "seq_scan_pct": seq_scan_pct,
            }
        )
        if plugin is not UNSET:
            field_dict["plugin"] = plugin
        if last_vacuum is not UNSET:
            field_dict["last_vacuum"] = last_vacuum
        if last_analyze is not UNSET:
            field_dict["last_analyze"] = last_analyze

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        schema = d.pop("schema")

        name = d.pop("name")

        total_size_mb = d.pop("total_size_mb")

        data_mb = d.pop("data_mb")

        index_mb = d.pop("index_mb")

        rows = d.pop("rows")

        dead_rows = d.pop("dead_rows")

        dead_pct = d.pop("dead_pct")

        seq_scan_count = d.pop("seq_scan_count")

        idx_scan_count = d.pop("idx_scan_count")

        seq_scan_pct = d.pop("seq_scan_pct")

        def _parse_plugin(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        plugin = _parse_plugin(d.pop("plugin", UNSET))

        def _parse_last_vacuum(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_vacuum = _parse_last_vacuum(d.pop("last_vacuum", UNSET))

        def _parse_last_analyze(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_analyze = _parse_last_analyze(d.pop("last_analyze", UNSET))

        table_stat = cls(
            schema=schema,
            name=name,
            total_size_mb=total_size_mb,
            data_mb=data_mb,
            index_mb=index_mb,
            rows=rows,
            dead_rows=dead_rows,
            dead_pct=dead_pct,
            seq_scan_count=seq_scan_count,
            idx_scan_count=idx_scan_count,
            seq_scan_pct=seq_scan_pct,
            plugin=plugin,
            last_vacuum=last_vacuum,
            last_analyze=last_analyze,
        )

        table_stat.additional_properties = d
        return table_stat

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
