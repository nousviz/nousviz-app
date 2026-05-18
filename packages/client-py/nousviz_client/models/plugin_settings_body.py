from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.plugin_setting_value import PluginSettingValue


T = TypeVar("T", bound="PluginSettingsBody")


@_attrs_define
class PluginSettingsBody:
    """
    Attributes:
        settings (list[PluginSettingValue]):
    """

    settings: list[PluginSettingValue]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        settings = []
        for settings_item_data in self.settings:
            settings_item = settings_item_data.to_dict()
            settings.append(settings_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "settings": settings,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.plugin_setting_value import PluginSettingValue

        d = dict(src_dict)
        settings = []
        _settings = d.pop("settings")
        for settings_item_data in _settings:
            settings_item = PluginSettingValue.from_dict(settings_item_data)

            settings.append(settings_item)

        plugin_settings_body = cls(
            settings=settings,
        )

        plugin_settings_body.additional_properties = d
        return plugin_settings_body

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
