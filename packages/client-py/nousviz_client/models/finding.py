from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.finding_severity import FindingSeverity
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.finding_action import FindingAction
    from ..models.finding_affected import FindingAffected


T = TypeVar("T", bound="Finding")


@_attrs_define
class Finding:
    """One actionable issue surfaced by the diagnostic engine.

    Attributes:
        id (str): Stable rule identifier (used for dedup, history lookup).
        severity (FindingSeverity):
        title (str): One-line summary shown collapsed.
        evidence (str): 2-4 lines explaining what was measured and why it triggered the rule.
        recommendation (str): Plain-language guidance — what to do about it.
        detected_at (str):
        affected (list[FindingAffected] | Unset):
        action (FindingAction | None | Unset):
        last_alerted_at (None | str | Unset): B274 (v0.9.11.20): ISO timestamp of the most recent webhook alert
            dispatched for this (finding_id, affected_key). Null when no alert has fired (severity below threshold, or the
            subscription set is empty). Drives the `alert sent N min ago` badge on the FindingCard.
    """

    id: str
    severity: FindingSeverity
    title: str
    evidence: str
    recommendation: str
    detected_at: str
    affected: list[FindingAffected] | Unset = UNSET
    action: FindingAction | None | Unset = UNSET
    last_alerted_at: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.finding_action import FindingAction

        id = self.id

        severity = self.severity.value

        title = self.title

        evidence = self.evidence

        recommendation = self.recommendation

        detected_at = self.detected_at

        affected: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.affected, Unset):
            affected = []
            for affected_item_data in self.affected:
                affected_item = affected_item_data.to_dict()
                affected.append(affected_item)

        action: dict[str, Any] | None | Unset
        if isinstance(self.action, Unset):
            action = UNSET
        elif isinstance(self.action, FindingAction):
            action = self.action.to_dict()
        else:
            action = self.action

        last_alerted_at: None | str | Unset
        if isinstance(self.last_alerted_at, Unset):
            last_alerted_at = UNSET
        else:
            last_alerted_at = self.last_alerted_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "severity": severity,
                "title": title,
                "evidence": evidence,
                "recommendation": recommendation,
                "detected_at": detected_at,
            }
        )
        if affected is not UNSET:
            field_dict["affected"] = affected
        if action is not UNSET:
            field_dict["action"] = action
        if last_alerted_at is not UNSET:
            field_dict["last_alerted_at"] = last_alerted_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.finding_action import FindingAction
        from ..models.finding_affected import FindingAffected

        d = dict(src_dict)
        id = d.pop("id")

        severity = FindingSeverity(d.pop("severity"))

        title = d.pop("title")

        evidence = d.pop("evidence")

        recommendation = d.pop("recommendation")

        detected_at = d.pop("detected_at")

        _affected = d.pop("affected", UNSET)
        affected: list[FindingAffected] | Unset = UNSET
        if _affected is not UNSET:
            affected = []
            for affected_item_data in _affected:
                affected_item = FindingAffected.from_dict(affected_item_data)

                affected.append(affected_item)

        def _parse_action(data: object) -> FindingAction | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                action_type_0 = FindingAction.from_dict(data)

                return action_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(FindingAction | None | Unset, data)

        action = _parse_action(d.pop("action", UNSET))

        def _parse_last_alerted_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_alerted_at = _parse_last_alerted_at(d.pop("last_alerted_at", UNSET))

        finding = cls(
            id=id,
            severity=severity,
            title=title,
            evidence=evidence,
            recommendation=recommendation,
            detected_at=detected_at,
            affected=affected,
            action=action,
            last_alerted_at=last_alerted_at,
        )

        finding.additional_properties = d
        return finding

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
