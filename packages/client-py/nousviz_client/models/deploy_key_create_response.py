from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DeployKeyCreateResponse")


@_attrs_define
class DeployKeyCreateResponse:
    """POST /api/settings/deploy-keys — returns the new key's identity + public material.

    The private key is encrypted with NOUSVIZ_ENCRYPTION_KEY and stored;
    the response intentionally omits it.

        Attributes:
            id (str):
            name (str):
            host (str):
            public_key (str):
            fingerprint (str):
    """

    id: str
    name: str
    host: str
    public_key: str
    fingerprint: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        host = self.host

        public_key = self.public_key

        fingerprint = self.fingerprint

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "host": host,
                "public_key": public_key,
                "fingerprint": fingerprint,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        host = d.pop("host")

        public_key = d.pop("public_key")

        fingerprint = d.pop("fingerprint")

        deploy_key_create_response = cls(
            id=id,
            name=name,
            host=host,
            public_key=public_key,
            fingerprint=fingerprint,
        )

        deploy_key_create_response.additional_properties = d
        return deploy_key_create_response

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
