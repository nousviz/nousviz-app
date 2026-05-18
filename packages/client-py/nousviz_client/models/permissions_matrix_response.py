from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.permissions_matrix_response_audit_summary import PermissionsMatrixResponseAuditSummary
    from ..models.permissions_matrix_response_permissions import PermissionsMatrixResponsePermissions
    from ..models.permissions_matrix_response_role_data import PermissionsMatrixResponseRoleData
    from ..models.permissions_matrix_response_roles import PermissionsMatrixResponseRoles
    from ..models.permissions_matrix_response_routes_item import PermissionsMatrixResponseRoutesItem


T = TypeVar("T", bound="PermissionsMatrixResponse")


@_attrs_define
class PermissionsMatrixResponse:
    """GET /api/system/permissions — full RBAC registry snapshot.

    Used by the audit matrix UI on /system/permissions. The deep
    blocks (role_data, routes, audit_summary) are typed as
    dict[str, Any] / list[dict[str, Any]] because they carry per-role
    and per-route metadata whose shape varies (built-in vs custom
    roles, overrides present vs absent, etc.).

        Attributes:
            permissions (PermissionsMatrixResponsePermissions): Map of permission name -> {description, sensitive: bool}.
            roles (PermissionsMatrixResponseRoles): Backward-compatible flat map of role -> resolved permissions.
            role_data (PermissionsMatrixResponseRoleData): Per-role metadata: kind (built_in|custom), display_name,
                default_permissions, resolved permissions, override deltas, and (for custom roles) created_by + created_at.
            routes (list[PermissionsMatrixResponseRoutesItem]): Each registered route's permission + per-role last-accessed
                timestamps.
            public_routes (list[list[str]]): Routes that bypass auth — list of [method, path] pairs.
            audit_summary (PermissionsMatrixResponseAuditSummary): Allow/deny/shadow-mismatch counts + top-denial
                permissions over a window.
            shadow_mode (bool): True iff RBAC is running in shadow mode (decisions logged but not enforced).
            version (str): Platform version string at the time of the snapshot.
    """

    permissions: PermissionsMatrixResponsePermissions
    roles: PermissionsMatrixResponseRoles
    role_data: PermissionsMatrixResponseRoleData
    routes: list[PermissionsMatrixResponseRoutesItem]
    public_routes: list[list[str]]
    audit_summary: PermissionsMatrixResponseAuditSummary
    shadow_mode: bool
    version: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        permissions = self.permissions.to_dict()

        roles = self.roles.to_dict()

        role_data = self.role_data.to_dict()

        routes = []
        for routes_item_data in self.routes:
            routes_item = routes_item_data.to_dict()
            routes.append(routes_item)

        public_routes = []
        for public_routes_item_data in self.public_routes:
            public_routes_item = public_routes_item_data

            public_routes.append(public_routes_item)

        audit_summary = self.audit_summary.to_dict()

        shadow_mode = self.shadow_mode

        version = self.version

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "permissions": permissions,
                "roles": roles,
                "role_data": role_data,
                "routes": routes,
                "public_routes": public_routes,
                "audit_summary": audit_summary,
                "shadow_mode": shadow_mode,
                "version": version,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.permissions_matrix_response_audit_summary import PermissionsMatrixResponseAuditSummary
        from ..models.permissions_matrix_response_permissions import PermissionsMatrixResponsePermissions
        from ..models.permissions_matrix_response_role_data import PermissionsMatrixResponseRoleData
        from ..models.permissions_matrix_response_roles import PermissionsMatrixResponseRoles
        from ..models.permissions_matrix_response_routes_item import PermissionsMatrixResponseRoutesItem

        d = dict(src_dict)
        permissions = PermissionsMatrixResponsePermissions.from_dict(d.pop("permissions"))

        roles = PermissionsMatrixResponseRoles.from_dict(d.pop("roles"))

        role_data = PermissionsMatrixResponseRoleData.from_dict(d.pop("role_data"))

        routes = []
        _routes = d.pop("routes")
        for routes_item_data in _routes:
            routes_item = PermissionsMatrixResponseRoutesItem.from_dict(routes_item_data)

            routes.append(routes_item)

        public_routes = []
        _public_routes = d.pop("public_routes")
        for public_routes_item_data in _public_routes:
            public_routes_item = cast(list[str], public_routes_item_data)

            public_routes.append(public_routes_item)

        audit_summary = PermissionsMatrixResponseAuditSummary.from_dict(d.pop("audit_summary"))

        shadow_mode = d.pop("shadow_mode")

        version = d.pop("version")

        permissions_matrix_response = cls(
            permissions=permissions,
            roles=roles,
            role_data=role_data,
            routes=routes,
            public_routes=public_routes,
            audit_summary=audit_summary,
            shadow_mode=shadow_mode,
            version=version,
        )

        permissions_matrix_response.additional_properties = d
        return permissions_matrix_response

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
