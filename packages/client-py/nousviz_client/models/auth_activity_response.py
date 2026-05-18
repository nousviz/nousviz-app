from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.auth_activity_row import AuthActivityRow


T = TypeVar("T", bound="AuthActivityResponse")


@_attrs_define
class AuthActivityResponse:
    """GET /api/auth/activity — admin-only audit view.

    Attributes:
        activity (list[AuthActivityRow]):
    """

    activity: list[AuthActivityRow]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        activity = []
        for activity_item_data in self.activity:
            activity_item = activity_item_data.to_dict()
            activity.append(activity_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "activity": activity,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.auth_activity_row import AuthActivityRow

        d = dict(src_dict)
        activity = []
        _activity = d.pop("activity")
        for activity_item_data in _activity:
            activity_item = AuthActivityRow.from_dict(activity_item_data)

            activity.append(activity_item)

        auth_activity_response = cls(
            activity=activity,
        )

        auth_activity_response.additional_properties = d
        return auth_activity_response

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
