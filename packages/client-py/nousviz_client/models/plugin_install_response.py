from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.plugin_entry import PluginEntry


T = TypeVar("T", bound="PluginInstallResponse")


@_attrs_define
class PluginInstallResponse:
    """POST /api/plugins/{id}/install — success path.

    Returns `status='already_installed'` when the plugin's directory
    already exists (idempotent). Otherwise `status='installed'` with
    the manifest plus migrations + route-load status.

        Attributes:
            status (str): 'installed' | 'already_installed'.
            plugin (PluginEntry): Single plugin entry from /plugins or /plugins/{id}.

                Carries the consistent envelope (id, version, display_name, status)
                plus any number of plugin-author-defined fields (dashboards,
                datasets, actions, settings, capabilities, …). The `extra='allow'`
                config is intentional — plugin manifests are open-ended.
            migrations_applied (list[str] | None | Unset):
            routes_active (bool | None | Unset):
    """

    status: str
    plugin: PluginEntry
    migrations_applied: list[str] | None | Unset = UNSET
    routes_active: bool | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        plugin = self.plugin.to_dict()

        migrations_applied: list[str] | None | Unset
        if isinstance(self.migrations_applied, Unset):
            migrations_applied = UNSET
        elif isinstance(self.migrations_applied, list):
            migrations_applied = self.migrations_applied

        else:
            migrations_applied = self.migrations_applied

        routes_active: bool | None | Unset
        if isinstance(self.routes_active, Unset):
            routes_active = UNSET
        else:
            routes_active = self.routes_active

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "plugin": plugin,
            }
        )
        if migrations_applied is not UNSET:
            field_dict["migrations_applied"] = migrations_applied
        if routes_active is not UNSET:
            field_dict["routes_active"] = routes_active

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.plugin_entry import PluginEntry

        d = dict(src_dict)
        status = d.pop("status")

        plugin = PluginEntry.from_dict(d.pop("plugin"))

        def _parse_migrations_applied(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                migrations_applied_type_0 = cast(list[str], data)

                return migrations_applied_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        migrations_applied = _parse_migrations_applied(d.pop("migrations_applied", UNSET))

        def _parse_routes_active(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        routes_active = _parse_routes_active(d.pop("routes_active", UNSET))

        plugin_install_response = cls(
            status=status,
            plugin=plugin,
            migrations_applied=migrations_applied,
            routes_active=routes_active,
        )

        plugin_install_response.additional_properties = d
        return plugin_install_response

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
