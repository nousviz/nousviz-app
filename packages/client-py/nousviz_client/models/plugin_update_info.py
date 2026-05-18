from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PluginUpdateInfo")


@_attrs_define
class PluginUpdateInfo:
    """Cached plugin update status for one plugin (B144).

    Attributes:
        plugin_id (str):
        source_class (str): 'first_party' | 'github' | 'pending' — origin of the update check.
        source_url (None | str | Unset):
        installed_version (None | str | Unset):
        latest_version (None | str | Unset):
        update_available (bool | Unset):  Default: False.
        last_error (None | str | Unset):
    """

    plugin_id: str
    source_class: str
    source_url: None | str | Unset = UNSET
    installed_version: None | str | Unset = UNSET
    latest_version: None | str | Unset = UNSET
    update_available: bool | Unset = False
    last_error: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        source_class = self.source_class

        source_url: None | str | Unset
        if isinstance(self.source_url, Unset):
            source_url = UNSET
        else:
            source_url = self.source_url

        installed_version: None | str | Unset
        if isinstance(self.installed_version, Unset):
            installed_version = UNSET
        else:
            installed_version = self.installed_version

        latest_version: None | str | Unset
        if isinstance(self.latest_version, Unset):
            latest_version = UNSET
        else:
            latest_version = self.latest_version

        update_available = self.update_available

        last_error: None | str | Unset
        if isinstance(self.last_error, Unset):
            last_error = UNSET
        else:
            last_error = self.last_error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "source_class": source_class,
            }
        )
        if source_url is not UNSET:
            field_dict["source_url"] = source_url
        if installed_version is not UNSET:
            field_dict["installed_version"] = installed_version
        if latest_version is not UNSET:
            field_dict["latest_version"] = latest_version
        if update_available is not UNSET:
            field_dict["update_available"] = update_available
        if last_error is not UNSET:
            field_dict["last_error"] = last_error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        source_class = d.pop("source_class")

        def _parse_source_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        source_url = _parse_source_url(d.pop("source_url", UNSET))

        def _parse_installed_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        installed_version = _parse_installed_version(d.pop("installed_version", UNSET))

        def _parse_latest_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        latest_version = _parse_latest_version(d.pop("latest_version", UNSET))

        update_available = d.pop("update_available", UNSET)

        def _parse_last_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_error = _parse_last_error(d.pop("last_error", UNSET))

        plugin_update_info = cls(
            plugin_id=plugin_id,
            source_class=source_class,
            source_url=source_url,
            installed_version=installed_version,
            latest_version=latest_version,
            update_available=update_available,
            last_error=last_error,
        )

        plugin_update_info.additional_properties = d
        return plugin_update_info

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
