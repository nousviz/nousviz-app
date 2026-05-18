from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SetupConfigRequest")


@_attrs_define
class SetupConfigRequest:
    """
    Attributes:
        auth_required (bool | Unset):  Default: True.
        postgres_password (None | str | Unset):
        generate_encryption_key (bool | Unset):  Default: False.
    """

    auth_required: bool | Unset = True
    postgres_password: None | str | Unset = UNSET
    generate_encryption_key: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        auth_required = self.auth_required

        postgres_password: None | str | Unset
        if isinstance(self.postgres_password, Unset):
            postgres_password = UNSET
        else:
            postgres_password = self.postgres_password

        generate_encryption_key = self.generate_encryption_key

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if auth_required is not UNSET:
            field_dict["auth_required"] = auth_required
        if postgres_password is not UNSET:
            field_dict["postgres_password"] = postgres_password
        if generate_encryption_key is not UNSET:
            field_dict["generate_encryption_key"] = generate_encryption_key

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        auth_required = d.pop("auth_required", UNSET)

        def _parse_postgres_password(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        postgres_password = _parse_postgres_password(d.pop("postgres_password", UNSET))

        generate_encryption_key = d.pop("generate_encryption_key", UNSET)

        setup_config_request = cls(
            auth_required=auth_required,
            postgres_password=postgres_password,
            generate_encryption_key=generate_encryption_key,
        )

        setup_config_request.additional_properties = d
        return setup_config_request

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
