from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DeployKeyCheckResponse")


@_attrs_define
class DeployKeyCheckResponse:
    """GET /api/settings/deploy-keys/check — does a key exist for `repo_url`?

    `match='repo'` indicates an exact-URL match (B204). The legacy
    host-fallback was removed; only exact URL hits return has_key=True.

        Attributes:
            has_key (bool):
            key_name (None | str | Unset):
            match (None | str | Unset): 'repo' for exact URL match.
    """

    has_key: bool
    key_name: None | str | Unset = UNSET
    match: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        has_key = self.has_key

        key_name: None | str | Unset
        if isinstance(self.key_name, Unset):
            key_name = UNSET
        else:
            key_name = self.key_name

        match: None | str | Unset
        if isinstance(self.match, Unset):
            match = UNSET
        else:
            match = self.match

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "has_key": has_key,
            }
        )
        if key_name is not UNSET:
            field_dict["key_name"] = key_name
        if match is not UNSET:
            field_dict["match"] = match

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        has_key = d.pop("has_key")

        def _parse_key_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        key_name = _parse_key_name(d.pop("key_name", UNSET))

        def _parse_match(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        match = _parse_match(d.pop("match", UNSET))

        deploy_key_check_response = cls(
            has_key=has_key,
            key_name=key_name,
            match=match,
        )

        deploy_key_check_response.additional_properties = d
        return deploy_key_check_response

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
