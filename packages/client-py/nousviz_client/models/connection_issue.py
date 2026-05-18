from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.connection_issue_detail_type_0 import ConnectionIssueDetailType0


T = TypeVar("T", bound="ConnectionIssue")


@_attrs_define
class ConnectionIssue:
    """A single banner-displayable connection health issue.

    Attributes:
        plugin_id (str):
        severity (str): 'warning' | 'error'
        message (str):
        detail (ConnectionIssueDetailType0 | None | Unset):
    """

    plugin_id: str
    severity: str
    message: str
    detail: ConnectionIssueDetailType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.connection_issue_detail_type_0 import ConnectionIssueDetailType0

        plugin_id = self.plugin_id

        severity = self.severity

        message = self.message

        detail: dict[str, Any] | None | Unset
        if isinstance(self.detail, Unset):
            detail = UNSET
        elif isinstance(self.detail, ConnectionIssueDetailType0):
            detail = self.detail.to_dict()
        else:
            detail = self.detail

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "severity": severity,
                "message": message,
            }
        )
        if detail is not UNSET:
            field_dict["detail"] = detail

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.connection_issue_detail_type_0 import ConnectionIssueDetailType0

        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        severity = d.pop("severity")

        message = d.pop("message")

        def _parse_detail(data: object) -> ConnectionIssueDetailType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                detail_type_0 = ConnectionIssueDetailType0.from_dict(data)

                return detail_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(ConnectionIssueDetailType0 | None | Unset, data)

        detail = _parse_detail(d.pop("detail", UNSET))

        connection_issue = cls(
            plugin_id=plugin_id,
            severity=severity,
            message=message,
            detail=detail,
        )

        connection_issue.additional_properties = d
        return connection_issue

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
