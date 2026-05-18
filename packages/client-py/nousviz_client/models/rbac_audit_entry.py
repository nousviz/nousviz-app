from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="RbacAuditEntry")


@_attrs_define
class RbacAuditEntry:
    """Single rbac_config_audit row — one RBAC config mutation.

    Attributes:
        id (int):
        occurred_at (str):
        action (str): One of 'grant', 'revoke', 'clear', 'create_role', 'delete_role', 'impersonate_start',
            'impersonate_end', 'password_reset_cli', 'password_reset_request', 'password_reset_completed',
            'password_change_self', 'acl_grant', 'acl_revoke', 'set_default_policy'.
        actor_user_id (None | str | Unset):
        actor_email (None | str | Unset):
        actor_role (None | str | Unset):
        target_role (None | str | Unset):
        target_permission (None | str | Unset):
        target_resource_type (None | str | Unset): B248 (v0.9.10.7): present on acl_grant / acl_revoke /
            set_default_policy rows.
        target_resource_id (None | str | Unset): B248 (v0.9.10.7): present on acl_grant / acl_revoke rows.
        before_state (Any | None | Unset): JSONB before-state — shape depends on the action.
        after_state (Any | None | Unset): JSONB after-state — shape depends on the action.
        note (None | str | Unset):
    """

    id: int
    occurred_at: str
    action: str
    actor_user_id: None | str | Unset = UNSET
    actor_email: None | str | Unset = UNSET
    actor_role: None | str | Unset = UNSET
    target_role: None | str | Unset = UNSET
    target_permission: None | str | Unset = UNSET
    target_resource_type: None | str | Unset = UNSET
    target_resource_id: None | str | Unset = UNSET
    before_state: Any | None | Unset = UNSET
    after_state: Any | None | Unset = UNSET
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        occurred_at = self.occurred_at

        action = self.action

        actor_user_id: None | str | Unset
        if isinstance(self.actor_user_id, Unset):
            actor_user_id = UNSET
        else:
            actor_user_id = self.actor_user_id

        actor_email: None | str | Unset
        if isinstance(self.actor_email, Unset):
            actor_email = UNSET
        else:
            actor_email = self.actor_email

        actor_role: None | str | Unset
        if isinstance(self.actor_role, Unset):
            actor_role = UNSET
        else:
            actor_role = self.actor_role

        target_role: None | str | Unset
        if isinstance(self.target_role, Unset):
            target_role = UNSET
        else:
            target_role = self.target_role

        target_permission: None | str | Unset
        if isinstance(self.target_permission, Unset):
            target_permission = UNSET
        else:
            target_permission = self.target_permission

        target_resource_type: None | str | Unset
        if isinstance(self.target_resource_type, Unset):
            target_resource_type = UNSET
        else:
            target_resource_type = self.target_resource_type

        target_resource_id: None | str | Unset
        if isinstance(self.target_resource_id, Unset):
            target_resource_id = UNSET
        else:
            target_resource_id = self.target_resource_id

        before_state: Any | None | Unset
        if isinstance(self.before_state, Unset):
            before_state = UNSET
        else:
            before_state = self.before_state

        after_state: Any | None | Unset
        if isinstance(self.after_state, Unset):
            after_state = UNSET
        else:
            after_state = self.after_state

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "occurred_at": occurred_at,
                "action": action,
            }
        )
        if actor_user_id is not UNSET:
            field_dict["actor_user_id"] = actor_user_id
        if actor_email is not UNSET:
            field_dict["actor_email"] = actor_email
        if actor_role is not UNSET:
            field_dict["actor_role"] = actor_role
        if target_role is not UNSET:
            field_dict["target_role"] = target_role
        if target_permission is not UNSET:
            field_dict["target_permission"] = target_permission
        if target_resource_type is not UNSET:
            field_dict["target_resource_type"] = target_resource_type
        if target_resource_id is not UNSET:
            field_dict["target_resource_id"] = target_resource_id
        if before_state is not UNSET:
            field_dict["before_state"] = before_state
        if after_state is not UNSET:
            field_dict["after_state"] = after_state
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        occurred_at = d.pop("occurred_at")

        action = d.pop("action")

        def _parse_actor_user_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        actor_user_id = _parse_actor_user_id(d.pop("actor_user_id", UNSET))

        def _parse_actor_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        actor_email = _parse_actor_email(d.pop("actor_email", UNSET))

        def _parse_actor_role(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        actor_role = _parse_actor_role(d.pop("actor_role", UNSET))

        def _parse_target_role(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        target_role = _parse_target_role(d.pop("target_role", UNSET))

        def _parse_target_permission(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        target_permission = _parse_target_permission(d.pop("target_permission", UNSET))

        def _parse_target_resource_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        target_resource_type = _parse_target_resource_type(d.pop("target_resource_type", UNSET))

        def _parse_target_resource_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        target_resource_id = _parse_target_resource_id(d.pop("target_resource_id", UNSET))

        def _parse_before_state(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        before_state = _parse_before_state(d.pop("before_state", UNSET))

        def _parse_after_state(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        after_state = _parse_after_state(d.pop("after_state", UNSET))

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        rbac_audit_entry = cls(
            id=id,
            occurred_at=occurred_at,
            action=action,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            actor_role=actor_role,
            target_role=target_role,
            target_permission=target_permission,
            target_resource_type=target_resource_type,
            target_resource_id=target_resource_id,
            before_state=before_state,
            after_state=after_state,
            note=note,
        )

        rbac_audit_entry.additional_properties = d
        return rbac_audit_entry

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
