from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AnnotationDeleteResponse")


@_attrs_define
class AnnotationDeleteResponse:
    """DELETE /api/annotations/{annotation_id}.

    `permanent=true` actually deletes; default is soft-delete (archived=true).

        Attributes:
            permanent (bool):
            status (str | Unset): Always 'deleted' (soft or hard). Default: 'deleted'.
    """

    permanent: bool
    status: str | Unset = "deleted"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        permanent = self.permanent

        status = self.status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "permanent": permanent,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        permanent = d.pop("permanent")

        status = d.pop("status", UNSET)

        annotation_delete_response = cls(
            permanent=permanent,
            status=status,
        )

        annotation_delete_response.additional_properties = d
        return annotation_delete_response

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
