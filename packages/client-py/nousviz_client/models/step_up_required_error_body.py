from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="StepUpRequiredErrorBody")


@_attrs_define
class StepUpRequiredErrorBody:
    """The structured detail body returned by `requires_step_up` (B236)
    and `PATCH /api/auth/me` with password (B251). Frontend's StepUpController
    keys off `detail.error == 'stepup_required'` to pop the modal.

        Attributes:
            message (str): Human-readable explanation.
            error (str | Unset): Stable machine-readable error code. Default: 'stepup_required'.
    """

    message: str
    error: str | Unset = "stepup_required"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        message = self.message

        error = self.error

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "message": message,
            }
        )
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        message = d.pop("message")

        error = d.pop("error", UNSET)

        step_up_required_error_body = cls(
            message=message,
            error=error,
        )

        step_up_required_error_body.additional_properties = d
        return step_up_required_error_body

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
