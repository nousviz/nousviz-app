from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DatabaseSettingsResponse")


@_attrs_define
class DatabaseSettingsResponse:
    """GET /api/settings/database — current Postgres config without password.

    Attributes:
        host (str):
        port (str):
        db (str):
        user (str):
        sslmode (str):
    """

    host: str
    port: str
    db: str
    user: str
    sslmode: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        host = self.host

        port = self.port

        db = self.db

        user = self.user

        sslmode = self.sslmode

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "host": host,
                "port": port,
                "db": db,
                "user": user,
                "sslmode": sslmode,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        host = d.pop("host")

        port = d.pop("port")

        db = d.pop("db")

        user = d.pop("user")

        sslmode = d.pop("sslmode")

        database_settings_response = cls(
            host=host,
            port=port,
            db=db,
            user=user,
            sslmode=sslmode,
        )

        database_settings_response.additional_properties = d
        return database_settings_response

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
