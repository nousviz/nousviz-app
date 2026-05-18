from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SSLBlock")


@_attrs_define
class SSLBlock:
    """SSL config status when NOUSVIZ_SSL is set. Absent on HTTP-only deployments.

    Shape mirrors `_get_ssl_status()` in routes/health.py — `enabled`
    and `type` are always present; `domain` and `expires` are present
    when applicable.

        Attributes:
            enabled (bool): Always True when this block is present.
            type_ (str): SSL provisioning mode, e.g. 'letsencrypt'.
            domain (None | str | Unset): Configured domain when set.
            expires (None | str | Unset): Cert expiry as reported by `openssl x509 -enddate`. Present only when the cert is
                readable.
    """

    enabled: bool
    type_: str
    domain: None | str | Unset = UNSET
    expires: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        enabled = self.enabled

        type_ = self.type_

        domain: None | str | Unset
        if isinstance(self.domain, Unset):
            domain = UNSET
        else:
            domain = self.domain

        expires: None | str | Unset
        if isinstance(self.expires, Unset):
            expires = UNSET
        else:
            expires = self.expires

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "enabled": enabled,
                "type": type_,
            }
        )
        if domain is not UNSET:
            field_dict["domain"] = domain
        if expires is not UNSET:
            field_dict["expires"] = expires

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        enabled = d.pop("enabled")

        type_ = d.pop("type")

        def _parse_domain(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        domain = _parse_domain(d.pop("domain", UNSET))

        def _parse_expires(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        expires = _parse_expires(d.pop("expires", UNSET))

        ssl_block = cls(
            enabled=enabled,
            type_=type_,
            domain=domain,
            expires=expires,
        )

        ssl_block.additional_properties = d
        return ssl_block

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
