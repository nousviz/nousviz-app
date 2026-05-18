from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.connection_entry_values import ConnectionEntryValues
    from ..models.connection_field import ConnectionField


T = TypeVar("T", bound="ConnectionEntry")


@_attrs_define
class ConnectionEntry:
    """Single connection block in the get-connections response.

    Attributes:
        name (None | str | Unset):
        label (None | str | Unset):
        description (None | str | Unset):
        fields (list[ConnectionField] | Unset): Field declarations from plugin.yaml's connections.fields block.
        values (ConnectionEntryValues | Unset): Field values keyed by field name. Secret fields are masked as
            '••••••••'.
    """

    name: None | str | Unset = UNSET
    label: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    fields: list[ConnectionField] | Unset = UNSET
    values: ConnectionEntryValues | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        label: None | str | Unset
        if isinstance(self.label, Unset):
            label = UNSET
        else:
            label = self.label

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        fields: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.fields, Unset):
            fields = []
            for fields_item_data in self.fields:
                fields_item = fields_item_data.to_dict()
                fields.append(fields_item)

        values: dict[str, Any] | Unset = UNSET
        if not isinstance(self.values, Unset):
            values = self.values.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if label is not UNSET:
            field_dict["label"] = label
        if description is not UNSET:
            field_dict["description"] = description
        if fields is not UNSET:
            field_dict["fields"] = fields
        if values is not UNSET:
            field_dict["values"] = values

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.connection_entry_values import ConnectionEntryValues
        from ..models.connection_field import ConnectionField

        d = dict(src_dict)

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        label = _parse_label(d.pop("label", UNSET))

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        _fields = d.pop("fields", UNSET)
        fields: list[ConnectionField] | Unset = UNSET
        if _fields is not UNSET:
            fields = []
            for fields_item_data in _fields:
                fields_item = ConnectionField.from_dict(fields_item_data)

                fields.append(fields_item)

        _values = d.pop("values", UNSET)
        values: ConnectionEntryValues | Unset
        if isinstance(_values, Unset):
            values = UNSET
        else:
            values = ConnectionEntryValues.from_dict(_values)

        connection_entry = cls(
            name=name,
            label=label,
            description=description,
            fields=fields,
            values=values,
        )

        connection_entry.additional_properties = d
        return connection_entry

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
