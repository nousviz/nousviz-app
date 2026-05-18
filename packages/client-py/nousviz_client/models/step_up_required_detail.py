from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.step_up_required_error_body import StepUpRequiredErrorBody


T = TypeVar("T", bound="StepUpRequiredDetail")


@_attrs_define
class StepUpRequiredDetail:
    """401 response from any endpoint gated by `requires_step_up`.
    The `detail` field is a structured dict, not a string.

        Attributes:
            detail (StepUpRequiredErrorBody): The structured detail body returned by `requires_step_up` (B236)
                and `PATCH /api/auth/me` with password (B251). Frontend's StepUpController
                keys off `detail.error == 'stepup_required'` to pop the modal.
    """

    detail: StepUpRequiredErrorBody
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        detail = self.detail.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "detail": detail,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.step_up_required_error_body import StepUpRequiredErrorBody

        d = dict(src_dict)
        detail = StepUpRequiredErrorBody.from_dict(d.pop("detail"))

        step_up_required_detail = cls(
            detail=detail,
        )

        step_up_required_detail.additional_properties = d
        return step_up_required_detail

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
