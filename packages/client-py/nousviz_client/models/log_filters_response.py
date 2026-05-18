from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.log_filter_user import LogFilterUser


T = TypeVar("T", bound="LogFiltersResponse")


@_attrs_define
class LogFiltersResponse:
    """GET /api/admin/logs/filters — distinct values for dropdown filters.

    Limited to events from the last 30 days so the dropdowns don't
    accumulate stale plugin slugs or deleted users.

        Attributes:
            plugins (list[str]):
            users (list[LogFilterUser]):
    """

    plugins: list[str]
    users: list[LogFilterUser]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugins = self.plugins

        users = []
        for users_item_data in self.users:
            users_item = users_item_data.to_dict()
            users.append(users_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugins": plugins,
                "users": users,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.log_filter_user import LogFilterUser

        d = dict(src_dict)
        plugins = cast(list[str], d.pop("plugins"))

        users = []
        _users = d.pop("users")
        for users_item_data in _users:
            users_item = LogFilterUser.from_dict(users_item_data)

            users.append(users_item)

        log_filters_response = cls(
            plugins=plugins,
            users=users,
        )

        log_filters_response.additional_properties = d
        return log_filters_response

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
