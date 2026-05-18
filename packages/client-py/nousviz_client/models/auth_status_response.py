from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.user_serialized import UserSerialized


T = TypeVar("T", bound="AuthStatusResponse")


@_attrs_define
class AuthStatusResponse:
    """GET /api/auth/status — public endpoint, returns auth-mode info.

    Always returned, regardless of whether the caller is authenticated.
    `user` is null when no valid session token is presented.

        Attributes:
            authenticated (bool):
            auth_required (bool): True iff AUTH_REQUIRED=true in .env.
            users_exist (bool): True iff at least one user row exists.
            user (None | Unset | UserSerialized):
    """

    authenticated: bool
    auth_required: bool
    users_exist: bool
    user: None | Unset | UserSerialized = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.user_serialized import UserSerialized

        authenticated = self.authenticated

        auth_required = self.auth_required

        users_exist = self.users_exist

        user: dict[str, Any] | None | Unset
        if isinstance(self.user, Unset):
            user = UNSET
        elif isinstance(self.user, UserSerialized):
            user = self.user.to_dict()
        else:
            user = self.user

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "authenticated": authenticated,
                "auth_required": auth_required,
                "users_exist": users_exist,
            }
        )
        if user is not UNSET:
            field_dict["user"] = user

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.user_serialized import UserSerialized

        d = dict(src_dict)
        authenticated = d.pop("authenticated")

        auth_required = d.pop("auth_required")

        users_exist = d.pop("users_exist")

        def _parse_user(data: object) -> None | Unset | UserSerialized:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                user_type_0 = UserSerialized.from_dict(data)

                return user_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UserSerialized, data)

        user = _parse_user(d.pop("user", UNSET))

        auth_status_response = cls(
            authenticated=authenticated,
            auth_required=auth_required,
            users_exist=users_exist,
            user=user,
        )

        auth_status_response.additional_properties = d
        return auth_status_response

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
