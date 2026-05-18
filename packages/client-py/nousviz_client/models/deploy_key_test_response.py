from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DeployKeyTestResponse")


@_attrs_define
class DeployKeyTestResponse:
    """POST /api/settings/deploy-keys/{key_id}/test — SSH-auth probe.

    `ok=True` means GitHub responded 'successfully authenticated'. The
    `detail` carries either the short SSH stderr or a timeout / failure
    description.

        Attributes:
            ok (bool):
            detail (str): Truncated SSH output (200 chars) or error description.
    """

    ok: bool
    detail: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ok = self.ok

        detail = self.detail

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ok": ok,
                "detail": detail,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        ok = d.pop("ok")

        detail = d.pop("detail")

        deploy_key_test_response = cls(
            ok=ok,
            detail=detail,
        )

        deploy_key_test_response.additional_properties = d
        return deploy_key_test_response

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
