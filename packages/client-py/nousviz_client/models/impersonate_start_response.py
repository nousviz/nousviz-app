from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.user_serialized import UserSerialized


T = TypeVar("T", bound="ImpersonateStartResponse")


@_attrs_define
class ImpersonateStartResponse:
    """POST /api/auth/impersonate/{user_id}.

    NOTE: no `token` field. The caller's existing session token is
    reused with `acting_as_user_id` set on the session row (B254).

        Attributes:
            acting_as (UserSerialized): Serialized user row — output of `_serialize()` in routes/auth.py.

                `password_hash` is always stripped. `api_key` is truncated to first
                8 chars + ellipsis. Datetimes are ISO-8601 strings.

                Extra keys are allowed because user rows include columns added by
                later migrations (e.g. `last_seen_at`, `color`) that may or may not
                be present depending on schema state.
            acting_as_until (str):
    """

    acting_as: UserSerialized
    acting_as_until: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        acting_as = self.acting_as.to_dict()

        acting_as_until = self.acting_as_until

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "acting_as": acting_as,
                "acting_as_until": acting_as_until,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.user_serialized import UserSerialized

        d = dict(src_dict)
        acting_as = UserSerialized.from_dict(d.pop("acting_as"))

        acting_as_until = d.pop("acting_as_until")

        impersonate_start_response = cls(
            acting_as=acting_as,
            acting_as_until=acting_as_until,
        )

        impersonate_start_response.additional_properties = d
        return impersonate_start_response

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
