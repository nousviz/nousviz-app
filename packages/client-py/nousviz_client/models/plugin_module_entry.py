from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.plugin_module_dashboard import PluginModuleDashboard
    from ..models.plugin_module_navigation import PluginModuleNavigation


T = TypeVar("T", bound="PluginModuleEntry")


@_attrs_define
class PluginModuleEntry:
    """A single plugin module (sub-package within a plugin).

    Attributes:
        name (str):
        display_name (str):
        enabled (bool):
        enabled_by_default (bool):
        has_routes (bool):
        has_settings (bool):
        description (None | str | Unset):
        version (None | str | Unset):
        dashboards (list[PluginModuleDashboard] | Unset): Dashboards declared in module.yaml.
        navigation (list[PluginModuleNavigation] | Unset): Navigation entries declared in module.yaml.
        tables (list[str] | Unset): Postgres tables owned by this module (from module.yaml databases.postgres.tables).
        settings (list[Any] | Unset): Setting declarations from module.yaml — shape varies.
    """

    name: str
    display_name: str
    enabled: bool
    enabled_by_default: bool
    has_routes: bool
    has_settings: bool
    description: None | str | Unset = UNSET
    version: None | str | Unset = UNSET
    dashboards: list[PluginModuleDashboard] | Unset = UNSET
    navigation: list[PluginModuleNavigation] | Unset = UNSET
    tables: list[str] | Unset = UNSET
    settings: list[Any] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        display_name = self.display_name

        enabled = self.enabled

        enabled_by_default = self.enabled_by_default

        has_routes = self.has_routes

        has_settings = self.has_settings

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        version: None | str | Unset
        if isinstance(self.version, Unset):
            version = UNSET
        else:
            version = self.version

        dashboards: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.dashboards, Unset):
            dashboards = []
            for dashboards_item_data in self.dashboards:
                dashboards_item = dashboards_item_data.to_dict()
                dashboards.append(dashboards_item)

        navigation: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.navigation, Unset):
            navigation = []
            for navigation_item_data in self.navigation:
                navigation_item = navigation_item_data.to_dict()
                navigation.append(navigation_item)

        tables: list[str] | Unset = UNSET
        if not isinstance(self.tables, Unset):
            tables = self.tables

        settings: list[Any] | Unset = UNSET
        if not isinstance(self.settings, Unset):
            settings = self.settings

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "display_name": display_name,
                "enabled": enabled,
                "enabled_by_default": enabled_by_default,
                "has_routes": has_routes,
                "has_settings": has_settings,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if version is not UNSET:
            field_dict["version"] = version
        if dashboards is not UNSET:
            field_dict["dashboards"] = dashboards
        if navigation is not UNSET:
            field_dict["navigation"] = navigation
        if tables is not UNSET:
            field_dict["tables"] = tables
        if settings is not UNSET:
            field_dict["settings"] = settings

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.plugin_module_dashboard import PluginModuleDashboard
        from ..models.plugin_module_navigation import PluginModuleNavigation

        d = dict(src_dict)
        name = d.pop("name")

        display_name = d.pop("display_name")

        enabled = d.pop("enabled")

        enabled_by_default = d.pop("enabled_by_default")

        has_routes = d.pop("has_routes")

        has_settings = d.pop("has_settings")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        version = _parse_version(d.pop("version", UNSET))

        _dashboards = d.pop("dashboards", UNSET)
        dashboards: list[PluginModuleDashboard] | Unset = UNSET
        if _dashboards is not UNSET:
            dashboards = []
            for dashboards_item_data in _dashboards:
                dashboards_item = PluginModuleDashboard.from_dict(dashboards_item_data)

                dashboards.append(dashboards_item)

        _navigation = d.pop("navigation", UNSET)
        navigation: list[PluginModuleNavigation] | Unset = UNSET
        if _navigation is not UNSET:
            navigation = []
            for navigation_item_data in _navigation:
                navigation_item = PluginModuleNavigation.from_dict(navigation_item_data)

                navigation.append(navigation_item)

        tables = cast(list[str], d.pop("tables", UNSET))

        settings = cast(list[Any], d.pop("settings", UNSET))

        plugin_module_entry = cls(
            name=name,
            display_name=display_name,
            enabled=enabled,
            enabled_by_default=enabled_by_default,
            has_routes=has_routes,
            has_settings=has_settings,
            description=description,
            version=version,
            dashboards=dashboards,
            navigation=navigation,
            tables=tables,
            settings=settings,
        )

        plugin_module_entry.additional_properties = d
        return plugin_module_entry

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
