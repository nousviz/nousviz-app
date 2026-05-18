from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="EmailSettingsResponse")


@_attrs_define
class EmailSettingsResponse:
    """GET /api/settings/email — SMTP config without password.

    Attributes:
        host (str):
        port (str):
        username (str):
        from_address (str):
        from_name (str):
        use_tls (str):
        configured (bool):
    """

    host: str
    port: str
    username: str
    from_address: str
    from_name: str
    use_tls: str
    configured: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        host = self.host

        port = self.port

        username = self.username

        from_address = self.from_address

        from_name = self.from_name

        use_tls = self.use_tls

        configured = self.configured

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "host": host,
                "port": port,
                "username": username,
                "from_address": from_address,
                "from_name": from_name,
                "use_tls": use_tls,
                "configured": configured,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        host = d.pop("host")

        port = d.pop("port")

        username = d.pop("username")

        from_address = d.pop("from_address")

        from_name = d.pop("from_name")

        use_tls = d.pop("use_tls")

        configured = d.pop("configured")

        email_settings_response = cls(
            host=host,
            port=port,
            username=username,
            from_address=from_address,
            from_name=from_name,
            use_tls=use_tls,
            configured=configured,
        )

        email_settings_response.additional_properties = d
        return email_settings_response

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
