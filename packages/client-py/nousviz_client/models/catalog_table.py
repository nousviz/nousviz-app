from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.catalog_column import CatalogColumn


T = TypeVar("T", bound="CatalogTable")


@_attrs_define
class CatalogTable:
    """A single discovered table — output of `catalog.Table.to_dict()`.

    Attributes:
        name (str):
        plugin_id (str):
        table_type (None | str | Unset): 'BASE TABLE' | 'VIEW'.
        row_count_estimate (int | None | Unset):
        columns (list[CatalogColumn] | Unset): Column metadata from information_schema, ordered by ordinal_position.
    """

    name: str
    plugin_id: str
    table_type: None | str | Unset = UNSET
    row_count_estimate: int | None | Unset = UNSET
    columns: list[CatalogColumn] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        plugin_id = self.plugin_id

        table_type: None | str | Unset
        if isinstance(self.table_type, Unset):
            table_type = UNSET
        else:
            table_type = self.table_type

        row_count_estimate: int | None | Unset
        if isinstance(self.row_count_estimate, Unset):
            row_count_estimate = UNSET
        else:
            row_count_estimate = self.row_count_estimate

        columns: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.columns, Unset):
            columns = []
            for columns_item_data in self.columns:
                columns_item = columns_item_data.to_dict()
                columns.append(columns_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "plugin_id": plugin_id,
            }
        )
        if table_type is not UNSET:
            field_dict["table_type"] = table_type
        if row_count_estimate is not UNSET:
            field_dict["row_count_estimate"] = row_count_estimate
        if columns is not UNSET:
            field_dict["columns"] = columns

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.catalog_column import CatalogColumn

        d = dict(src_dict)
        name = d.pop("name")

        plugin_id = d.pop("plugin_id")

        def _parse_table_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        table_type = _parse_table_type(d.pop("table_type", UNSET))

        def _parse_row_count_estimate(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        row_count_estimate = _parse_row_count_estimate(d.pop("row_count_estimate", UNSET))

        _columns = d.pop("columns", UNSET)
        columns: list[CatalogColumn] | Unset = UNSET
        if _columns is not UNSET:
            columns = []
            for columns_item_data in _columns:
                columns_item = CatalogColumn.from_dict(columns_item_data)

                columns.append(columns_item)

        catalog_table = cls(
            name=name,
            plugin_id=plugin_id,
            table_type=table_type,
            row_count_estimate=row_count_estimate,
            columns=columns,
        )

        catalog_table.additional_properties = d
        return catalog_table

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
