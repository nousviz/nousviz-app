from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.invite_row import InviteRow


T = TypeVar("T", bound="InviteCreateResponse")


@_attrs_define
class InviteCreateResponse:
    """POST /api/auth/users/invite — invite issued.

    `invite_url` is exposed only when email send failed (operator can
    copy/paste the link). On successful send, it stays null and only
    `email_sent=true` is reported.

        Attributes:
            invite (InviteRow): A single user_invites row.
            email_sent (bool):
            invite_url (None | str | Unset):
            email_error (None | str | Unset):
    """

    invite: InviteRow
    email_sent: bool
    invite_url: None | str | Unset = UNSET
    email_error: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        invite = self.invite.to_dict()

        email_sent = self.email_sent

        invite_url: None | str | Unset
        if isinstance(self.invite_url, Unset):
            invite_url = UNSET
        else:
            invite_url = self.invite_url

        email_error: None | str | Unset
        if isinstance(self.email_error, Unset):
            email_error = UNSET
        else:
            email_error = self.email_error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "invite": invite,
                "email_sent": email_sent,
            }
        )
        if invite_url is not UNSET:
            field_dict["invite_url"] = invite_url
        if email_error is not UNSET:
            field_dict["email_error"] = email_error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.invite_row import InviteRow

        d = dict(src_dict)
        invite = InviteRow.from_dict(d.pop("invite"))

        email_sent = d.pop("email_sent")

        def _parse_invite_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        invite_url = _parse_invite_url(d.pop("invite_url", UNSET))

        def _parse_email_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        email_error = _parse_email_error(d.pop("email_error", UNSET))

        invite_create_response = cls(
            invite=invite,
            email_sent=email_sent,
            invite_url=invite_url,
            email_error=email_error,
        )

        invite_create_response.additional_properties = d
        return invite_create_response

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
