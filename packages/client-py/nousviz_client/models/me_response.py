from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.user_serialized import UserSerialized


T = TypeVar("T", bound="MeResponse")


@_attrs_define
class MeResponse:
    """GET /api/auth/me — Option B identity shape (B236).

    The top-level fields describe the ACTOR (the human authenticated to
    this session). `acting_as`, when present, carries the target the
    actor is currently impersonating.

    Frontend reads `me` for actor identity (for the impersonation
    banner, audit display, log-out button) and `me.acting_as` for
    effective identity (permission resolution, role display). The
    `useEffectiveIdentity()` hook centralizes this choice.

        Attributes:
            id (str):
            email (str):
            role (str):
            name (None | str | Unset):
            is_active (bool | None | Unset):
            avatar_url (None | str | Unset):
            auth_method (None | str | Unset):
            created_at (None | str | Unset):
            last_login (None | str | Unset):
            login_count (int | None | Unset):
            acting_as (None | Unset | UserSerialized): Target user when the session is impersonating; absent otherwise.
    """

    id: str
    email: str
    role: str
    name: None | str | Unset = UNSET
    is_active: bool | None | Unset = UNSET
    avatar_url: None | str | Unset = UNSET
    auth_method: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    last_login: None | str | Unset = UNSET
    login_count: int | None | Unset = UNSET
    acting_as: None | Unset | UserSerialized = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.user_serialized import UserSerialized

        id = self.id

        email = self.email

        role = self.role

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        is_active: bool | None | Unset
        if isinstance(self.is_active, Unset):
            is_active = UNSET
        else:
            is_active = self.is_active

        avatar_url: None | str | Unset
        if isinstance(self.avatar_url, Unset):
            avatar_url = UNSET
        else:
            avatar_url = self.avatar_url

        auth_method: None | str | Unset
        if isinstance(self.auth_method, Unset):
            auth_method = UNSET
        else:
            auth_method = self.auth_method

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        last_login: None | str | Unset
        if isinstance(self.last_login, Unset):
            last_login = UNSET
        else:
            last_login = self.last_login

        login_count: int | None | Unset
        if isinstance(self.login_count, Unset):
            login_count = UNSET
        else:
            login_count = self.login_count

        acting_as: dict[str, Any] | None | Unset
        if isinstance(self.acting_as, Unset):
            acting_as = UNSET
        elif isinstance(self.acting_as, UserSerialized):
            acting_as = self.acting_as.to_dict()
        else:
            acting_as = self.acting_as

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "email": email,
                "role": role,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name
        if is_active is not UNSET:
            field_dict["is_active"] = is_active
        if avatar_url is not UNSET:
            field_dict["avatar_url"] = avatar_url
        if auth_method is not UNSET:
            field_dict["auth_method"] = auth_method
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if last_login is not UNSET:
            field_dict["last_login"] = last_login
        if login_count is not UNSET:
            field_dict["login_count"] = login_count
        if acting_as is not UNSET:
            field_dict["acting_as"] = acting_as

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.user_serialized import UserSerialized

        d = dict(src_dict)
        id = d.pop("id")

        email = d.pop("email")

        role = d.pop("role")

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_is_active(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        is_active = _parse_is_active(d.pop("is_active", UNSET))

        def _parse_avatar_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        avatar_url = _parse_avatar_url(d.pop("avatar_url", UNSET))

        def _parse_auth_method(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        auth_method = _parse_auth_method(d.pop("auth_method", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_last_login(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_login = _parse_last_login(d.pop("last_login", UNSET))

        def _parse_login_count(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        login_count = _parse_login_count(d.pop("login_count", UNSET))

        def _parse_acting_as(data: object) -> None | Unset | UserSerialized:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                acting_as_type_0 = UserSerialized.from_dict(data)

                return acting_as_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UserSerialized, data)

        acting_as = _parse_acting_as(d.pop("acting_as", UNSET))

        me_response = cls(
            id=id,
            email=email,
            role=role,
            name=name,
            is_active=is_active,
            avatar_url=avatar_url,
            auth_method=auth_method,
            created_at=created_at,
            last_login=last_login,
            login_count=login_count,
            acting_as=acting_as,
        )

        me_response.additional_properties = d
        return me_response

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
