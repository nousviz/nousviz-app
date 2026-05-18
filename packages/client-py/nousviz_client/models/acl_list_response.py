from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.acl_grant_row import AclGrantRow


T = TypeVar("T", bound="AclListResponse")


@_attrs_define
class AclListResponse:
    """GET /api/resource-acls/{type}/{id}.

    Attributes:
        resource_type (str):
        resource_id (str):
        default_policy (str):
        grants (list[AclGrantRow]):
    """

    resource_type: str
    resource_id: str
    default_policy: str
    grants: list[AclGrantRow]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        resource_type = self.resource_type

        resource_id = self.resource_id

        default_policy = self.default_policy

        grants = []
        for grants_item_data in self.grants:
            grants_item = grants_item_data.to_dict()
            grants.append(grants_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "default_policy": default_policy,
                "grants": grants,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.acl_grant_row import AclGrantRow

        d = dict(src_dict)
        resource_type = d.pop("resource_type")

        resource_id = d.pop("resource_id")

        default_policy = d.pop("default_policy")

        grants = []
        _grants = d.pop("grants")
        for grants_item_data in _grants:
            grants_item = AclGrantRow.from_dict(grants_item_data)

            grants.append(grants_item)

        acl_list_response = cls(
            resource_type=resource_type,
            resource_id=resource_id,
            default_policy=default_policy,
            grants=grants,
        )

        acl_list_response.additional_properties = d
        return acl_list_response

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
