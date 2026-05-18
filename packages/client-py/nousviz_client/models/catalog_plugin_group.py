from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.catalog_table import CatalogTable


T = TypeVar("T", bound="CatalogPluginGroup")


@_attrs_define
class CatalogPluginGroup:
    """All discovered tables for one plugin — used by /catalog/tables.

    Attributes:
        id (str): Plugin slug.
        tables (list[CatalogTable]):
    """

    id: str
    tables: list[CatalogTable]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        tables = []
        for tables_item_data in self.tables:
            tables_item = tables_item_data.to_dict()
            tables.append(tables_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "tables": tables,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.catalog_table import CatalogTable

        d = dict(src_dict)
        id = d.pop("id")

        tables = []
        _tables = d.pop("tables")
        for tables_item_data in _tables:
            tables_item = CatalogTable.from_dict(tables_item_data)

            tables.append(tables_item)

        catalog_plugin_group = cls(
            id=id,
            tables=tables,
        )

        catalog_plugin_group.additional_properties = d
        return catalog_plugin_group

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
