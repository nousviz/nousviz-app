from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="UpdateRetentionPolicyBody")


@_attrs_define
class UpdateRetentionPolicyBody:
    """PUT /api/maintenance/retention/{policy_key} body.

    Either field may be omitted; pass only what's changing.

        Attributes:
            retention_days (int | None | Unset): New retention threshold (0 means immediate purge of additional_where
                matches).
            paused (bool | None | Unset): True to pause the policy; false to activate.
    """

    retention_days: int | None | Unset = UNSET
    paused: bool | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        retention_days: int | None | Unset
        if isinstance(self.retention_days, Unset):
            retention_days = UNSET
        else:
            retention_days = self.retention_days

        paused: bool | None | Unset
        if isinstance(self.paused, Unset):
            paused = UNSET
        else:
            paused = self.paused

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if retention_days is not UNSET:
            field_dict["retention_days"] = retention_days
        if paused is not UNSET:
            field_dict["paused"] = paused

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_retention_days(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        retention_days = _parse_retention_days(d.pop("retention_days", UNSET))

        def _parse_paused(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        paused = _parse_paused(d.pop("paused", UNSET))

        update_retention_policy_body = cls(
            retention_days=retention_days,
            paused=paused,
        )

        update_retention_policy_body.additional_properties = d
        return update_retention_policy_body

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
