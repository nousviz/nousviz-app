from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.connection_issue import ConnectionIssue


T = TypeVar("T", bound="ConnectionHealthResponse")


@_attrs_define
class ConnectionHealthResponse:
    """List of banner-shaped connection health issues across plugins.

    Attributes:
        issues (list[ConnectionIssue] | Unset): May be empty when no plugin reports an issue.
    """

    issues: list[ConnectionIssue] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        issues: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.issues, Unset):
            issues = []
            for issues_item_data in self.issues:
                issues_item = issues_item_data.to_dict()
                issues.append(issues_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if issues is not UNSET:
            field_dict["issues"] = issues

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.connection_issue import ConnectionIssue

        d = dict(src_dict)
        _issues = d.pop("issues", UNSET)
        issues: list[ConnectionIssue] | Unset = UNSET
        if _issues is not UNSET:
            issues = []
            for issues_item_data in _issues:
                issues_item = ConnectionIssue.from_dict(issues_item_data)

                issues.append(issues_item)

        connection_health_response = cls(
            issues=issues,
        )

        connection_health_response.additional_properties = d
        return connection_health_response

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
