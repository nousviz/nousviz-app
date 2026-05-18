from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DatabaseSettings")


@_attrs_define
class DatabaseSettings:
    """
    Attributes:
        host (str):
        port (int):
        db (str):
        user (str):
        password (None | str | Unset):
        sslmode (str | Unset):  Default: 'prefer'.
    """

    host: str
    port: int
    db: str
    user: str
    password: None | str | Unset = UNSET
    sslmode: str | Unset = "prefer"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        host = self.host

        port = self.port

        db = self.db

        user = self.user

        password: None | str | Unset
        if isinstance(self.password, Unset):
            password = UNSET
        else:
            password = self.password

        sslmode = self.sslmode

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "host": host,
                "port": port,
                "db": db,
                "user": user,
            }
        )
        if password is not UNSET:
            field_dict["password"] = password
        if sslmode is not UNSET:
            field_dict["sslmode"] = sslmode

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        host = d.pop("host")

        port = d.pop("port")

        db = d.pop("db")

        user = d.pop("user")

        def _parse_password(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        password = _parse_password(d.pop("password", UNSET))

        sslmode = d.pop("sslmode", UNSET)

        database_settings = cls(
            host=host,
            port=port,
            db=db,
            user=user,
            password=password,
            sslmode=sslmode,
        )

        database_settings.additional_properties = d
        return database_settings

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
