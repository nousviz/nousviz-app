from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.plugin_module_entry import PluginModuleEntry


T = TypeVar("T", bound="PluginModulesListResponse")


@_attrs_define
class PluginModulesListResponse:
    """GET /api/plugins/{id}/modules.

    Attributes:
        modules (list[PluginModuleEntry]):
    """

    modules: list[PluginModuleEntry]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        modules = []
        for modules_item_data in self.modules:
            modules_item = modules_item_data.to_dict()
            modules.append(modules_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "modules": modules,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.plugin_module_entry import PluginModuleEntry

        d = dict(src_dict)
        modules = []
        _modules = d.pop("modules")
        for modules_item_data in _modules:
            modules_item = PluginModuleEntry.from_dict(modules_item_data)

            modules.append(modules_item)

        plugin_modules_list_response = cls(
            modules=modules,
        )

        plugin_modules_list_response.additional_properties = d
        return plugin_modules_list_response

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
