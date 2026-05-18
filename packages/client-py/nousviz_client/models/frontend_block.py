from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.frontend_component import FrontendComponent


T = TypeVar("T", bound="FrontendBlock")


@_attrs_define
class FrontendBlock:
    """Frontend trust + component declarations (B151).

    Attributes:
        trusted (bool):
        needs_consent (bool):
        components (list[FrontendComponent] | Unset): React components declared in the plugin's frontend.components
            manifest block.
        admin_proxy (bool | Unset): B304 (v0.10.0.5): plugin opts into the path-scoped admin-session cookie auth path.
            When true, the auth middleware accepts a nv_admin_<slug> cookie for requests under /api/plugins/<slug>/admin/*
            in addition to the existing X-Session-Token / X-API-Key headers. Cookies are minted by the plugin's own bridge
            endpoint via nousviz_sdk.auth.issue_admin_session_cookie(). Default false: middleware enforces header-based auth
            as today. Default: False.
    """

    trusted: bool
    needs_consent: bool
    components: list[FrontendComponent] | Unset = UNSET
    admin_proxy: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        trusted = self.trusted

        needs_consent = self.needs_consent

        components: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.components, Unset):
            components = []
            for components_item_data in self.components:
                components_item = components_item_data.to_dict()
                components.append(components_item)

        admin_proxy = self.admin_proxy

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "trusted": trusted,
                "needs_consent": needs_consent,
            }
        )
        if components is not UNSET:
            field_dict["components"] = components
        if admin_proxy is not UNSET:
            field_dict["admin_proxy"] = admin_proxy

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.frontend_component import FrontendComponent

        d = dict(src_dict)
        trusted = d.pop("trusted")

        needs_consent = d.pop("needs_consent")

        _components = d.pop("components", UNSET)
        components: list[FrontendComponent] | Unset = UNSET
        if _components is not UNSET:
            components = []
            for components_item_data in _components:
                components_item = FrontendComponent.from_dict(components_item_data)

                components.append(components_item)

        admin_proxy = d.pop("admin_proxy", UNSET)

        frontend_block = cls(
            trusted=trusted,
            needs_consent=needs_consent,
            components=components,
            admin_proxy=admin_proxy,
        )

        frontend_block.additional_properties = d
        return frontend_block

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
