from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.dataport_tab_index_entry import DataportTabIndexEntry


T = TypeVar("T", bound="DataportPluginIndexEntry")


@_attrs_define
class DataportPluginIndexEntry:
    """A single plugin in the dataport index — slug + tab labels.

    Attributes:
        slug (str):
        tabs (list[DataportTabIndexEntry]):
    """

    slug: str
    tabs: list[DataportTabIndexEntry]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        slug = self.slug

        tabs = []
        for tabs_item_data in self.tabs:
            tabs_item = tabs_item_data.to_dict()
            tabs.append(tabs_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "slug": slug,
                "tabs": tabs,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dataport_tab_index_entry import DataportTabIndexEntry

        d = dict(src_dict)
        slug = d.pop("slug")

        tabs = []
        _tabs = d.pop("tabs")
        for tabs_item_data in _tabs:
            tabs_item = DataportTabIndexEntry.from_dict(tabs_item_data)

            tabs.append(tabs_item)

        dataport_plugin_index_entry = cls(
            slug=slug,
            tabs=tabs,
        )

        dataport_plugin_index_entry.additional_properties = d
        return dataport_plugin_index_entry

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
