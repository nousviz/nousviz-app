from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ImpersonateExitResponse")


@_attrs_define
class ImpersonateExitResponse:
    """POST /api/auth/impersonate/exit — idempotent, always returns 200.

    Attributes:
        was_impersonating (bool):
        ok (bool | Unset):  Default: True.
    """

    was_impersonating: bool
    ok: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        was_impersonating = self.was_impersonating

        ok = self.ok

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "wasImpersonating": was_impersonating,
            }
        )
        if ok is not UNSET:
            field_dict["ok"] = ok

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        was_impersonating = d.pop("wasImpersonating")

        ok = d.pop("ok", UNSET)

        impersonate_exit_response = cls(
            was_impersonating=was_impersonating,
            ok=ok,
        )

        impersonate_exit_response.additional_properties = d
        return impersonate_exit_response

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
