from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.catalog_table import CatalogTable


T = TypeVar("T", bound="CatalogPluginTablesResponse")


@_attrs_define
class CatalogPluginTablesResponse:
    """GET /api/catalog/plugins/{plugin_id}/tables.

    Returns empty `tables` (not 404) when the plugin has no discovered
    tables, so the frontend can render an empty state.

        Attributes:
            plugin_id (str):
            tables (list[CatalogTable]):
            manifest_drift (Any | Unset): Output of catalog.detect_manifest_drift — shape varies, may be null.
    """

    plugin_id: str
    tables: list[CatalogTable]
    manifest_drift: Any | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        tables = []
        for tables_item_data in self.tables:
            tables_item = tables_item_data.to_dict()
            tables.append(tables_item)

        manifest_drift = self.manifest_drift

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "tables": tables,
            }
        )
        if manifest_drift is not UNSET:
            field_dict["manifest_drift"] = manifest_drift

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.catalog_table import CatalogTable

        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        tables = []
        _tables = d.pop("tables")
        for tables_item_data in _tables:
            tables_item = CatalogTable.from_dict(tables_item_data)

            tables.append(tables_item)

        manifest_drift = d.pop("manifest_drift", UNSET)

        catalog_plugin_tables_response = cls(
            plugin_id=plugin_id,
            tables=tables,
            manifest_drift=manifest_drift,
        )

        catalog_plugin_tables_response.additional_properties = d
        return catalog_plugin_tables_response

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
