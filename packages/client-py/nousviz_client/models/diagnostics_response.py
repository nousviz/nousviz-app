from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.diagnostics_summary import DiagnosticsSummary
    from ..models.finding import Finding


T = TypeVar("T", bound="DiagnosticsResponse")


@_attrs_define
class DiagnosticsResponse:
    """GET /api/system/diagnostics.

    Attributes:
        collected_at (str):
        summary (DiagnosticsSummary):
        findings (list[Finding]):
    """

    collected_at: str
    summary: DiagnosticsSummary
    findings: list[Finding]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        collected_at = self.collected_at

        summary = self.summary.to_dict()

        findings = []
        for findings_item_data in self.findings:
            findings_item = findings_item_data.to_dict()
            findings.append(findings_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "collected_at": collected_at,
                "summary": summary,
                "findings": findings,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.diagnostics_summary import DiagnosticsSummary
        from ..models.finding import Finding

        d = dict(src_dict)
        collected_at = d.pop("collected_at")

        summary = DiagnosticsSummary.from_dict(d.pop("summary"))

        findings = []
        _findings = d.pop("findings")
        for findings_item_data in _findings:
            findings_item = Finding.from_dict(findings_item_data)

            findings.append(findings_item)

        diagnostics_response = cls(
            collected_at=collected_at,
            summary=summary,
            findings=findings,
        )

        diagnostics_response.additional_properties = d
        return diagnostics_response

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
