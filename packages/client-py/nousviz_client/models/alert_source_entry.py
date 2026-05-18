from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.alert_column import AlertColumn


T = TypeVar("T", bound="AlertSourceEntry")


@_attrs_define
class AlertSourceEntry:
    """Single source entry under postgres / connections / plugins.

    Attributes:
        id (str):
        label (str):
        source_type (str): 'postgres' | 'plugin_postgres' | 'plugin' | 'connection'.
        source_label (str):
        plugin_id (None | str | Unset):
        table (None | str | Unset):
        columns (list[AlertColumn] | Unset): Column metadata when introspectable (postgres + plugin_postgres); empty for
            connection sources.
    """

    id: str
    label: str
    source_type: str
    source_label: str
    plugin_id: None | str | Unset = UNSET
    table: None | str | Unset = UNSET
    columns: list[AlertColumn] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        label = self.label

        source_type = self.source_type

        source_label = self.source_label

        plugin_id: None | str | Unset
        if isinstance(self.plugin_id, Unset):
            plugin_id = UNSET
        else:
            plugin_id = self.plugin_id

        table: None | str | Unset
        if isinstance(self.table, Unset):
            table = UNSET
        else:
            table = self.table

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
                "id": id,
                "label": label,
                "source_type": source_type,
                "source_label": source_label,
            }
        )
        if plugin_id is not UNSET:
            field_dict["plugin_id"] = plugin_id
        if table is not UNSET:
            field_dict["table"] = table
        if columns is not UNSET:
            field_dict["columns"] = columns

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alert_column import AlertColumn

        d = dict(src_dict)
        id = d.pop("id")

        label = d.pop("label")

        source_type = d.pop("source_type")

        source_label = d.pop("source_label")

        def _parse_plugin_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        plugin_id = _parse_plugin_id(d.pop("plugin_id", UNSET))

        def _parse_table(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        table = _parse_table(d.pop("table", UNSET))

        _columns = d.pop("columns", UNSET)
        columns: list[AlertColumn] | Unset = UNSET
        if _columns is not UNSET:
            columns = []
            for columns_item_data in _columns:
                columns_item = AlertColumn.from_dict(columns_item_data)

                columns.append(columns_item)

        alert_source_entry = cls(
            id=id,
            label=label,
            source_type=source_type,
            source_label=source_label,
            plugin_id=plugin_id,
            table=table,
            columns=columns,
        )

        alert_source_entry.additional_properties = d
        return alert_source_entry

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
