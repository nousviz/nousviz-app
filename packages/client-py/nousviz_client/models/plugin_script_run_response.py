from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PluginScriptRunResponse")


@_attrs_define
class PluginScriptRunResponse:
    """Result of running a plugin's setup_schema.py or health_check.py.

    Both endpoints return the same shape: subprocess exit code plus
    combined stdout+stderr. `status` is 'success' on returncode 0,
    'error' otherwise. Used by the plugin Settings tab to surface the
    setup/health output to the operator.

        Attributes:
            status (str): 'success' | 'error' (derived from subprocess exit code).
            output (str): Combined stdout + stderr from the plugin script.
            exit_code (int): The subprocess exit code.
    """

    status: str
    output: str
    exit_code: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        output = self.output

        exit_code = self.exit_code

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "output": output,
                "exit_code": exit_code,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        status = d.pop("status")

        output = d.pop("output")

        exit_code = d.pop("exit_code")

        plugin_script_run_response = cls(
            status=status,
            output=output,
            exit_code=exit_code,
        )

        plugin_script_run_response.additional_properties = d
        return plugin_script_run_response

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
