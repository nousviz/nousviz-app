from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.uninstall_check_data_dir import UninstallCheckDataDir
    from ..models.uninstall_check_dependent import UninstallCheckDependent
    from ..models.uninstall_check_table import UninstallCheckTable
    from ..models.uninstall_check_table_with_size import UninstallCheckTableWithSize


T = TypeVar("T", bound="UninstallCheckResponse")


@_attrs_define
class UninstallCheckResponse:
    """GET /api/plugins/{id}/uninstall-check — info for the confirmation modal.

    Attributes:
        plugin_id (str):
        display_name (str):
        has_dependents (bool):
        has_references (bool):
        has_data (bool):
        type_ (None | str | Unset):
        dependents (list[UninstallCheckDependent] | Unset): Other installed plugins that depend on this one —
            uninstalling without cascade is blocked.
        references (list[Any] | Unset): External references to this plugin (fusions, dashboards, etc.).
        tables (list[UninstallCheckTable] | Unset): DB tables that would be dropped if remove_data=true.
        data_dirs (list[UninstallCheckDataDir] | Unset): Filesystem data dirs under data/{slug}/ (utility plugins).
        tables_to_drop_if_data_removed (list[UninstallCheckTableWithSize] | Unset): Each Postgres table the plugin
            declares with its current size + row count. Drives the 'exactly what will be dropped' disclosure on the
            uninstall modal.
        tables_to_drop_total_size_mb (float | Unset): Sum of size_mb across tables_to_drop_if_data_removed. Default:
            0.0.
        tables_to_drop_total_count (int | Unset): len(tables_to_drop_if_data_removed). Frontend uses this to decide
            whether to render the DELETE button at all. Default: 0.
    """

    plugin_id: str
    display_name: str
    has_dependents: bool
    has_references: bool
    has_data: bool
    type_: None | str | Unset = UNSET
    dependents: list[UninstallCheckDependent] | Unset = UNSET
    references: list[Any] | Unset = UNSET
    tables: list[UninstallCheckTable] | Unset = UNSET
    data_dirs: list[UninstallCheckDataDir] | Unset = UNSET
    tables_to_drop_if_data_removed: list[UninstallCheckTableWithSize] | Unset = UNSET
    tables_to_drop_total_size_mb: float | Unset = 0.0
    tables_to_drop_total_count: int | Unset = 0
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        display_name = self.display_name

        has_dependents = self.has_dependents

        has_references = self.has_references

        has_data = self.has_data

        type_: None | str | Unset
        if isinstance(self.type_, Unset):
            type_ = UNSET
        else:
            type_ = self.type_

        dependents: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.dependents, Unset):
            dependents = []
            for dependents_item_data in self.dependents:
                dependents_item = dependents_item_data.to_dict()
                dependents.append(dependents_item)

        references: list[Any] | Unset = UNSET
        if not isinstance(self.references, Unset):
            references = self.references

        tables: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.tables, Unset):
            tables = []
            for tables_item_data in self.tables:
                tables_item = tables_item_data.to_dict()
                tables.append(tables_item)

        data_dirs: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.data_dirs, Unset):
            data_dirs = []
            for data_dirs_item_data in self.data_dirs:
                data_dirs_item = data_dirs_item_data.to_dict()
                data_dirs.append(data_dirs_item)

        tables_to_drop_if_data_removed: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.tables_to_drop_if_data_removed, Unset):
            tables_to_drop_if_data_removed = []
            for tables_to_drop_if_data_removed_item_data in self.tables_to_drop_if_data_removed:
                tables_to_drop_if_data_removed_item = tables_to_drop_if_data_removed_item_data.to_dict()
                tables_to_drop_if_data_removed.append(tables_to_drop_if_data_removed_item)

        tables_to_drop_total_size_mb = self.tables_to_drop_total_size_mb

        tables_to_drop_total_count = self.tables_to_drop_total_count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "display_name": display_name,
                "has_dependents": has_dependents,
                "has_references": has_references,
                "has_data": has_data,
            }
        )
        if type_ is not UNSET:
            field_dict["type"] = type_
        if dependents is not UNSET:
            field_dict["dependents"] = dependents
        if references is not UNSET:
            field_dict["references"] = references
        if tables is not UNSET:
            field_dict["tables"] = tables
        if data_dirs is not UNSET:
            field_dict["data_dirs"] = data_dirs
        if tables_to_drop_if_data_removed is not UNSET:
            field_dict["tables_to_drop_if_data_removed"] = tables_to_drop_if_data_removed
        if tables_to_drop_total_size_mb is not UNSET:
            field_dict["tables_to_drop_total_size_mb"] = tables_to_drop_total_size_mb
        if tables_to_drop_total_count is not UNSET:
            field_dict["tables_to_drop_total_count"] = tables_to_drop_total_count

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.uninstall_check_data_dir import UninstallCheckDataDir
        from ..models.uninstall_check_dependent import UninstallCheckDependent
        from ..models.uninstall_check_table import UninstallCheckTable
        from ..models.uninstall_check_table_with_size import UninstallCheckTableWithSize

        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        display_name = d.pop("display_name")

        has_dependents = d.pop("has_dependents")

        has_references = d.pop("has_references")

        has_data = d.pop("has_data")

        def _parse_type_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        type_ = _parse_type_(d.pop("type", UNSET))

        _dependents = d.pop("dependents", UNSET)
        dependents: list[UninstallCheckDependent] | Unset = UNSET
        if _dependents is not UNSET:
            dependents = []
            for dependents_item_data in _dependents:
                dependents_item = UninstallCheckDependent.from_dict(dependents_item_data)

                dependents.append(dependents_item)

        references = cast(list[Any], d.pop("references", UNSET))

        _tables = d.pop("tables", UNSET)
        tables: list[UninstallCheckTable] | Unset = UNSET
        if _tables is not UNSET:
            tables = []
            for tables_item_data in _tables:
                tables_item = UninstallCheckTable.from_dict(tables_item_data)

                tables.append(tables_item)

        _data_dirs = d.pop("data_dirs", UNSET)
        data_dirs: list[UninstallCheckDataDir] | Unset = UNSET
        if _data_dirs is not UNSET:
            data_dirs = []
            for data_dirs_item_data in _data_dirs:
                data_dirs_item = UninstallCheckDataDir.from_dict(data_dirs_item_data)

                data_dirs.append(data_dirs_item)

        _tables_to_drop_if_data_removed = d.pop("tables_to_drop_if_data_removed", UNSET)
        tables_to_drop_if_data_removed: list[UninstallCheckTableWithSize] | Unset = UNSET
        if _tables_to_drop_if_data_removed is not UNSET:
            tables_to_drop_if_data_removed = []
            for tables_to_drop_if_data_removed_item_data in _tables_to_drop_if_data_removed:
                tables_to_drop_if_data_removed_item = UninstallCheckTableWithSize.from_dict(
                    tables_to_drop_if_data_removed_item_data
                )

                tables_to_drop_if_data_removed.append(tables_to_drop_if_data_removed_item)

        tables_to_drop_total_size_mb = d.pop("tables_to_drop_total_size_mb", UNSET)

        tables_to_drop_total_count = d.pop("tables_to_drop_total_count", UNSET)

        uninstall_check_response = cls(
            plugin_id=plugin_id,
            display_name=display_name,
            has_dependents=has_dependents,
            has_references=has_references,
            has_data=has_data,
            type_=type_,
            dependents=dependents,
            references=references,
            tables=tables,
            data_dirs=data_dirs,
            tables_to_drop_if_data_removed=tables_to_drop_if_data_removed,
            tables_to_drop_total_size_mb=tables_to_drop_total_size_mb,
            tables_to_drop_total_count=tables_to_drop_total_count,
        )

        uninstall_check_response.additional_properties = d
        return uninstall_check_response

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
