from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="EmailSettings")


@_attrs_define
class EmailSettings:
    """
    Attributes:
        host (str):
        from_address (str):
        port (int | Unset):  Default: 587.
        username (str | Unset):  Default: ''.
        password (None | str | Unset):
        from_name (str | Unset):  Default: 'NousViz'.
        use_tls (bool | Unset):  Default: True.
    """

    host: str
    from_address: str
    port: int | Unset = 587
    username: str | Unset = ""
    password: None | str | Unset = UNSET
    from_name: str | Unset = "NousViz"
    use_tls: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        host = self.host

        from_address = self.from_address

        port = self.port

        username = self.username

        password: None | str | Unset
        if isinstance(self.password, Unset):
            password = UNSET
        else:
            password = self.password

        from_name = self.from_name

        use_tls = self.use_tls

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "host": host,
                "from_address": from_address,
            }
        )
        if port is not UNSET:
            field_dict["port"] = port
        if username is not UNSET:
            field_dict["username"] = username
        if password is not UNSET:
            field_dict["password"] = password
        if from_name is not UNSET:
            field_dict["from_name"] = from_name
        if use_tls is not UNSET:
            field_dict["use_tls"] = use_tls

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        host = d.pop("host")

        from_address = d.pop("from_address")

        port = d.pop("port", UNSET)

        username = d.pop("username", UNSET)

        def _parse_password(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        password = _parse_password(d.pop("password", UNSET))

        from_name = d.pop("from_name", UNSET)

        use_tls = d.pop("use_tls", UNSET)

        email_settings = cls(
            host=host,
            from_address=from_address,
            port=port,
            username=username,
            password=password,
            from_name=from_name,
            use_tls=use_tls,
        )

        email_settings.additional_properties = d
        return email_settings

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
