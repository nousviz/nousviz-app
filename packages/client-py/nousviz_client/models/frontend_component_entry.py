from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="FrontendComponentEntry")


@_attrs_define
class FrontendComponentEntry:
    """Augmented component entry — manifest declaration + on-disk presence.

    Attributes:
        name (str):
        path (str):
        filename (str):
        exists_on_disk (bool):
    """

    name: str
    path: str
    filename: str
    exists_on_disk: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        path = self.path

        filename = self.filename

        exists_on_disk = self.exists_on_disk

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "path": path,
                "filename": filename,
                "exists_on_disk": exists_on_disk,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        path = d.pop("path")

        filename = d.pop("filename")

        exists_on_disk = d.pop("exists_on_disk")

        frontend_component_entry = cls(
            name=name,
            path=path,
            filename=filename,
            exists_on_disk=exists_on_disk,
        )

        frontend_component_entry.additional_properties = d
        return frontend_component_entry

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
