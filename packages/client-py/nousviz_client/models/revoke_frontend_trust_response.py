from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="RevokeFrontendTrustResponse")


@_attrs_define
class RevokeFrontendTrustResponse:
    """POST /api/plugins/{id}/revoke-frontend-trust.

    Attributes:
        plugin_id (str):
        trusted (bool | Unset):  Default: False.
    """

    plugin_id: str
    trusted: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        trusted = self.trusted

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
            }
        )
        if trusted is not UNSET:
            field_dict["trusted"] = trusted

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        trusted = d.pop("trusted", UNSET)

        revoke_frontend_trust_response = cls(
            plugin_id=plugin_id,
            trusted=trusted,
        )

        revoke_frontend_trust_response.additional_properties = d
        return revoke_frontend_trust_response

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
