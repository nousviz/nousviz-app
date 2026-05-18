from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_connection_config import CreateConnectionConfig


T = TypeVar("T", bound="CreateConnection")


@_attrs_define
class CreateConnection:
    """
    Attributes:
        name (str):
        type_ (str):
        config (CreateConnectionConfig):
        is_default (bool | Unset):  Default: False.
        description (str | Unset):  Default: ''.
        tags (list[str] | Unset):
    """

    name: str
    type_: str
    config: CreateConnectionConfig
    is_default: bool | Unset = False
    description: str | Unset = ""
    tags: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        type_ = self.type_

        config = self.config.to_dict()

        is_default = self.is_default

        description = self.description

        tags: list[str] | Unset = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "type": type_,
                "config": config,
            }
        )
        if is_default is not UNSET:
            field_dict["is_default"] = is_default
        if description is not UNSET:
            field_dict["description"] = description
        if tags is not UNSET:
            field_dict["tags"] = tags

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_connection_config import CreateConnectionConfig

        d = dict(src_dict)
        name = d.pop("name")

        type_ = d.pop("type")

        config = CreateConnectionConfig.from_dict(d.pop("config"))

        is_default = d.pop("is_default", UNSET)

        description = d.pop("description", UNSET)

        tags = cast(list[str], d.pop("tags", UNSET))

        create_connection = cls(
            name=name,
            type_=type_,
            config=config,
            is_default=is_default,
            description=description,
            tags=tags,
        )

        create_connection.additional_properties = d
        return create_connection

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
