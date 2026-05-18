from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.plugin_setting_entry import PluginSettingEntry


T = TypeVar("T", bound="PluginSettingsResponse")


@_attrs_define
class PluginSettingsResponse:
    """GET /api/plugins/{id}/settings — current saved settings.

    `_conn.*` keys are excluded (they belong to the /connections surface).

        Attributes:
            settings (list[PluginSettingEntry] | Unset): Saved settings, one entry per declared key in the manifest's
                settings block.
    """

    settings: list[PluginSettingEntry] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        settings: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.settings, Unset):
            settings = []
            for settings_item_data in self.settings:
                settings_item = settings_item_data.to_dict()
                settings.append(settings_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if settings is not UNSET:
            field_dict["settings"] = settings

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.plugin_setting_entry import PluginSettingEntry

        d = dict(src_dict)
        _settings = d.pop("settings", UNSET)
        settings: list[PluginSettingEntry] | Unset = UNSET
        if _settings is not UNSET:
            settings = []
            for settings_item_data in _settings:
                settings_item = PluginSettingEntry.from_dict(settings_item_data)

                settings.append(settings_item)

        plugin_settings_response = cls(
            settings=settings,
        )

        plugin_settings_response.additional_properties = d
        return plugin_settings_response

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
