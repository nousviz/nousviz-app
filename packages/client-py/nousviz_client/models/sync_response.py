from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="SyncResponse")


@_attrs_define
class SyncResponse:
    """
    Attributes:
        status (str):
        output (str | Unset):  Default: ''.
        exit_code (int | None | Unset):
        run_id (int | None | Unset):
        enqueued (bool | Unset):  Default: False.
    """

    status: str
    output: str | Unset = ""
    exit_code: int | None | Unset = UNSET
    run_id: int | None | Unset = UNSET
    enqueued: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        output = self.output

        exit_code: int | None | Unset
        if isinstance(self.exit_code, Unset):
            exit_code = UNSET
        else:
            exit_code = self.exit_code

        run_id: int | None | Unset
        if isinstance(self.run_id, Unset):
            run_id = UNSET
        else:
            run_id = self.run_id

        enqueued = self.enqueued

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
            }
        )
        if output is not UNSET:
            field_dict["output"] = output
        if exit_code is not UNSET:
            field_dict["exit_code"] = exit_code
        if run_id is not UNSET:
            field_dict["run_id"] = run_id
        if enqueued is not UNSET:
            field_dict["enqueued"] = enqueued

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = d.pop("status")

        output = d.pop("output", UNSET)

        def _parse_exit_code(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        exit_code = _parse_exit_code(d.pop("exit_code", UNSET))

        def _parse_run_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        run_id = _parse_run_id(d.pop("run_id", UNSET))

        enqueued = d.pop("enqueued", UNSET)

        sync_response = cls(
            status=status,
            output=output,
            exit_code=exit_code,
            run_id=run_id,
            enqueued=enqueued,
        )

        sync_response.additional_properties = d
        return sync_response

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
