from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.frontend_component_entry import FrontendComponentEntry


T = TypeVar("T", bound="PluginFrontendComponentsResponse")


@_attrs_define
class PluginFrontendComponentsResponse:
    """GET /api/plugins/{id}/frontend-components.

    Attributes:
        plugin_id (str):
        components (list[FrontendComponentEntry]):
        trusted (bool):
        needs_consent (bool):
        admin_proxy (bool | Unset): B304 (v0.10.0.5): plugin opts into the path-scoped admin-session cookie auth path.
            Surfaced here so the trust banner can render the admin-proxy consent line. Default: False.
    """

    plugin_id: str
    components: list[FrontendComponentEntry]
    trusted: bool
    needs_consent: bool
    admin_proxy: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        components = []
        for components_item_data in self.components:
            components_item = components_item_data.to_dict()
            components.append(components_item)

        trusted = self.trusted

        needs_consent = self.needs_consent

        admin_proxy = self.admin_proxy

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "components": components,
                "trusted": trusted,
                "needs_consent": needs_consent,
            }
        )
        if admin_proxy is not UNSET:
            field_dict["admin_proxy"] = admin_proxy

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.frontend_component_entry import FrontendComponentEntry

        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        components = []
        _components = d.pop("components")
        for components_item_data in _components:
            components_item = FrontendComponentEntry.from_dict(components_item_data)

            components.append(components_item)

        trusted = d.pop("trusted")

        needs_consent = d.pop("needs_consent")

        admin_proxy = d.pop("admin_proxy", UNSET)

        plugin_frontend_components_response = cls(
            plugin_id=plugin_id,
            components=components,
            trusted=trusted,
            needs_consent=needs_consent,
            admin_proxy=admin_proxy,
        )

        plugin_frontend_components_response.additional_properties = d
        return plugin_frontend_components_response

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
