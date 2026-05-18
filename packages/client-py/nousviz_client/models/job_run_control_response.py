from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JobRunControlResponse")


@_attrs_define
class JobRunControlResponse:
    """POST /api/jobs/{run_id}/{cancel|pause|resume} response.

    `changed` is True when the operation moved the run into a new
    status; False when the operation was a no-op (e.g. cancelling an
    already-terminal run).

        Attributes:
            changed (bool):
            status (str): The run's status after the operation.
            ok (bool | Unset):  Default: True.
    """

    changed: bool
    status: str
    ok: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        changed = self.changed

        status = self.status

        ok = self.ok

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "changed": changed,
                "status": status,
            }
        )
        if ok is not UNSET:
            field_dict["ok"] = ok

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        changed = d.pop("changed")

        status = d.pop("status")

        ok = d.pop("ok", UNSET)

        job_run_control_response = cls(
            changed=changed,
            status=status,
            ok=ok,
        )

        job_run_control_response.additional_properties = d
        return job_run_control_response

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
