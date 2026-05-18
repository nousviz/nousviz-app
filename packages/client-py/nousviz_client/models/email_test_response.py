from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="EmailTestResponse")


@_attrs_define
class EmailTestResponse:
    """POST /api/settings/email/test — send a test email + report outcome.

    Attributes:
        ok (bool):
        error (None | str | Unset):
        sent_to (None | str | Unset):
    """

    ok: bool
    error: None | str | Unset = UNSET
    sent_to: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ok = self.ok

        error: None | str | Unset
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        sent_to: None | str | Unset
        if isinstance(self.sent_to, Unset):
            sent_to = UNSET
        else:
            sent_to = self.sent_to

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ok": ok,
            }
        )
        if error is not UNSET:
            field_dict["error"] = error
        if sent_to is not UNSET:
            field_dict["sent_to"] = sent_to

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        ok = d.pop("ok")

        def _parse_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error = _parse_error(d.pop("error", UNSET))

        def _parse_sent_to(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sent_to = _parse_sent_to(d.pop("sent_to", UNSET))

        email_test_response = cls(
            ok=ok,
            error=error,
            sent_to=sent_to,
        )

        email_test_response.additional_properties = d
        return email_test_response

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
