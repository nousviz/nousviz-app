from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.finding_action_type import FindingActionType
from ..types import UNSET, Unset

T = TypeVar("T", bound="FindingAction")


@_attrs_define
class FindingAction:
    """Action button on a finding card.

    Phase 1 (v0.9.11.18) supports `external` (link) and `manual`
    (copy-to-clipboard SQL/shell). The Phase 2 `sql_with_confirmation`
    type — execute privileged DROP / VACUUM via a confirmation modal
    — is deferred pending its own audit + RBAC review.

        Attributes:
            type_ (FindingActionType):
            label (str):
            url (None | str | Unset): Route URL for `external` actions.
            sql (None | str | Unset): SQL to copy-paste for `manual` actions.
            shell (None | str | Unset): Shell command for `manual` actions.
    """

    type_: FindingActionType
    label: str
    url: None | str | Unset = UNSET
    sql: None | str | Unset = UNSET
    shell: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        label = self.label

        url: None | str | Unset
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url

        sql: None | str | Unset
        if isinstance(self.sql, Unset):
            sql = UNSET
        else:
            sql = self.sql

        shell: None | str | Unset
        if isinstance(self.shell, Unset):
            shell = UNSET
        else:
            shell = self.shell

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "label": label,
            }
        )
        if url is not UNSET:
            field_dict["url"] = url
        if sql is not UNSET:
            field_dict["sql"] = sql
        if shell is not UNSET:
            field_dict["shell"] = shell

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = FindingActionType(d.pop("type"))

        label = d.pop("label")

        def _parse_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        url = _parse_url(d.pop("url", UNSET))

        def _parse_sql(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sql = _parse_sql(d.pop("sql", UNSET))

        def _parse_shell(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        shell = _parse_shell(d.pop("shell", UNSET))

        finding_action = cls(
            type_=type_,
            label=label,
            url=url,
            sql=sql,
            shell=shell,
        )

        finding_action.additional_properties = d
        return finding_action

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
