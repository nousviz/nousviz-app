from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CatalogColumn")


@_attrs_define
class CatalogColumn:
    """Column metadata from information_schema.

    Attributes:
        name (str):
        data_type (str):
        nullable (bool | None | Unset):
        default (None | str | Unset):
    """

    name: str
    data_type: str
    nullable: bool | None | Unset = UNSET
    default: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        data_type = self.data_type

        nullable: bool | None | Unset
        if isinstance(self.nullable, Unset):
            nullable = UNSET
        else:
            nullable = self.nullable

        default: None | str | Unset
        if isinstance(self.default, Unset):
            default = UNSET
        else:
            default = self.default

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "data_type": data_type,
            }
        )
        if nullable is not UNSET:
            field_dict["nullable"] = nullable
        if default is not UNSET:
            field_dict["default"] = default

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        data_type = d.pop("data_type")

        def _parse_nullable(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        nullable = _parse_nullable(d.pop("nullable", UNSET))

        def _parse_default(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        default = _parse_default(d.pop("default", UNSET))

        catalog_column = cls(
            name=name,
            data_type=data_type,
            nullable=nullable,
            default=default,
        )

        catalog_column.additional_properties = d
        return catalog_column

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
