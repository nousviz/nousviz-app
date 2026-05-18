from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.retention_run_all_response_summary import RetentionRunAllResponseSummary


T = TypeVar("T", bound="RetentionRunAllResponse")


@_attrs_define
class RetentionRunAllResponse:
    """POST /api/maintenance/retention/run-all response.

    Attributes:
        summary (RetentionRunAllResponseSummary): Per-policy outcome. int = rows_deleted; 'paused' = skipped; 'error:
            <type>' = failed.
        duration_ms (int):
    """

    summary: RetentionRunAllResponseSummary
    duration_ms: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        summary = self.summary.to_dict()

        duration_ms = self.duration_ms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "summary": summary,
                "duration_ms": duration_ms,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.retention_run_all_response_summary import RetentionRunAllResponseSummary

        d = dict(src_dict)
        summary = RetentionRunAllResponseSummary.from_dict(d.pop("summary"))

        duration_ms = d.pop("duration_ms")

        retention_run_all_response = cls(
            summary=summary,
            duration_ms=duration_ms,
        )

        retention_run_all_response.additional_properties = d
        return retention_run_all_response

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
