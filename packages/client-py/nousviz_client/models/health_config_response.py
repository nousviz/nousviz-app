from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="HealthConfigResponse")


@_attrs_define
class HealthConfigResponse:
    """Boolean status of security-sensitive config — never the values themselves.

    Attributes:
        encryption_key_set (bool): True iff NOUSVIZ_ENCRYPTION_KEY is set.
        auth_required (bool): True iff AUTH_REQUIRED=true in .env.
        superadmin_exists (bool): True iff at least one superadmin user row exists.
        postgres_password_is_default (bool): Always False since S108 (v0.8.1) — kept for response-shape back-compat.
        smtp_configured (bool): True iff SMTP_HOST is set.
        update_available (bool): True iff a newer release is available on GitHub.
        update_latest (None | str | Unset): Latest release tag if known.
        update_current (None | str | Unset): Currently-running version.
    """

    encryption_key_set: bool
    auth_required: bool
    superadmin_exists: bool
    postgres_password_is_default: bool
    smtp_configured: bool
    update_available: bool
    update_latest: None | str | Unset = UNSET
    update_current: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        encryption_key_set = self.encryption_key_set

        auth_required = self.auth_required

        superadmin_exists = self.superadmin_exists

        postgres_password_is_default = self.postgres_password_is_default

        smtp_configured = self.smtp_configured

        update_available = self.update_available

        update_latest: None | str | Unset
        if isinstance(self.update_latest, Unset):
            update_latest = UNSET
        else:
            update_latest = self.update_latest

        update_current: None | str | Unset
        if isinstance(self.update_current, Unset):
            update_current = UNSET
        else:
            update_current = self.update_current

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "encryption_key_set": encryption_key_set,
                "auth_required": auth_required,
                "superadmin_exists": superadmin_exists,
                "postgres_password_is_default": postgres_password_is_default,
                "smtp_configured": smtp_configured,
                "update_available": update_available,
            }
        )
        if update_latest is not UNSET:
            field_dict["update_latest"] = update_latest
        if update_current is not UNSET:
            field_dict["update_current"] = update_current

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        encryption_key_set = d.pop("encryption_key_set")

        auth_required = d.pop("auth_required")

        superadmin_exists = d.pop("superadmin_exists")

        postgres_password_is_default = d.pop("postgres_password_is_default")

        smtp_configured = d.pop("smtp_configured")

        update_available = d.pop("update_available")

        def _parse_update_latest(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        update_latest = _parse_update_latest(d.pop("update_latest", UNSET))

        def _parse_update_current(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        update_current = _parse_update_current(d.pop("update_current", UNSET))

        health_config_response = cls(
            encryption_key_set=encryption_key_set,
            auth_required=auth_required,
            superadmin_exists=superadmin_exists,
            postgres_password_is_default=postgres_password_is_default,
            smtp_configured=smtp_configured,
            update_available=update_available,
            update_latest=update_latest,
            update_current=update_current,
        )

        health_config_response.additional_properties = d
        return health_config_response

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
