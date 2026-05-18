from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.finding_history_point import FindingHistoryPoint


T = TypeVar("T", bound="DiagnosticsHistoryResponse")


@_attrs_define
class DiagnosticsHistoryResponse:
    """GET /api/system/diagnostics/history?id=...&days=N.

    Attributes:
        finding_id (str):
        days (int):
        points (list[FindingHistoryPoint]):
        first_detected_at (None | str | Unset): Earliest snapshot in the queried window where the finding was present.
            Null when the finding has never been present in the queried window.
    """

    finding_id: str
    days: int
    points: list[FindingHistoryPoint]
    first_detected_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        finding_id = self.finding_id

        days = self.days

        points = []
        for points_item_data in self.points:
            points_item = points_item_data.to_dict()
            points.append(points_item)

        first_detected_at: None | str | Unset
        if isinstance(self.first_detected_at, Unset):
            first_detected_at = UNSET
        else:
            first_detected_at = self.first_detected_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "finding_id": finding_id,
                "days": days,
                "points": points,
            }
        )
        if first_detected_at is not UNSET:
            field_dict["first_detected_at"] = first_detected_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.finding_history_point import FindingHistoryPoint

        d = dict(src_dict)
        finding_id = d.pop("finding_id")

        days = d.pop("days")

        points = []
        _points = d.pop("points")
        for points_item_data in _points:
            points_item = FindingHistoryPoint.from_dict(points_item_data)

            points.append(points_item)

        def _parse_first_detected_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        first_detected_at = _parse_first_detected_at(d.pop("first_detected_at", UNSET))

        diagnostics_history_response = cls(
            finding_id=finding_id,
            days=days,
            points=points,
            first_detected_at=first_detected_at,
        )

        diagnostics_history_response.additional_properties = d
        return diagnostics_history_response

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
