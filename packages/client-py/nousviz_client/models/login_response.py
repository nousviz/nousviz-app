from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.user_serialized import UserSerialized


T = TypeVar("T", bound="LoginResponse")


@_attrs_define
class LoginResponse:
    """POST /api/auth/login response.

    Attributes:
        token (str): Raw session token. Send as X-Session-Token on subsequent requests.
        expires_at (str): ISO-8601 expiry of the session.
        user (UserSerialized): Serialized user row — output of `_serialize()` in routes/auth.py.

            `password_hash` is always stripped. `api_key` is truncated to first
            8 chars + ellipsis. Datetimes are ISO-8601 strings.

            Extra keys are allowed because user rows include columns added by
            later migrations (e.g. `last_seen_at`, `color`) that may or may not
            be present depending on schema state.
    """

    token: str
    expires_at: str
    user: UserSerialized
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        token = self.token

        expires_at = self.expires_at

        user = self.user.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "token": token,
                "expires_at": expires_at,
                "user": user,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.user_serialized import UserSerialized

        d = dict(src_dict)
        token = d.pop("token")

        expires_at = d.pop("expires_at")

        user = UserSerialized.from_dict(d.pop("user"))

        login_response = cls(
            token=token,
            expires_at=expires_at,
            user=user,
        )

        login_response.additional_properties = d
        return login_response

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
