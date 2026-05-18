from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.frontend_component import FrontendComponent


T = TypeVar("T", bound="TrustFrontendResponse")


@_attrs_define
class TrustFrontendResponse:
    """POST /api/plugins/{id}/trust-frontend.

    Attributes:
        plugin_id (str):
        trusted (bool | Unset):  Default: True.
        components (list[FrontendComponent] | Unset): Components now permitted to render after operator trust grant.
    """

    plugin_id: str
    trusted: bool | Unset = True
    components: list[FrontendComponent] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        trusted = self.trusted

        components: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.components, Unset):
            components = []
            for components_item_data in self.components:
                components_item = components_item_data.to_dict()
                components.append(components_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
            }
        )
        if trusted is not UNSET:
            field_dict["trusted"] = trusted
        if components is not UNSET:
            field_dict["components"] = components

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.frontend_component import FrontendComponent

        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        trusted = d.pop("trusted", UNSET)

        _components = d.pop("components", UNSET)
        components: list[FrontendComponent] | Unset = UNSET
        if _components is not UNSET:
            components = []
            for components_item_data in _components:
                components_item = FrontendComponent.from_dict(components_item_data)

                components.append(components_item)

        trust_frontend_response = cls(
            plugin_id=plugin_id,
            trusted=trusted,
            components=components,
        )

        trust_frontend_response.additional_properties = d
        return trust_frontend_response

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
