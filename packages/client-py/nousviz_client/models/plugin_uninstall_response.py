from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.plugin_uninstall_response_data_tables_drop_failed_type_0_item import (
        PluginUninstallResponseDataTablesDropFailedType0Item,
    )
    from ..models.plugin_uninstall_response_references_cleanup_type_0 import (
        PluginUninstallResponseReferencesCleanupType0,
    )
    from ..models.uninstall_dependent import UninstallDependent


T = TypeVar("T", bound="PluginUninstallResponse")


@_attrs_define
class PluginUninstallResponse:
    """DELETE /api/plugins/{id}/install.

    Two response shapes:
    - `status='has_dependents'` (when other plugins depend on this one
      and `cascade=false`): the frontend should prompt the operator to
      confirm cascade or cancel. `dependents` lists the affected plugins.
    - `status='uninstalled'` (success): lists what was removed and
      whether data was kept or dropped.

        Attributes:
            status (str): 'uninstalled' | 'has_dependents'.
            dependents (list[UninstallDependent] | None | Unset):
            uninstalled (list[str] | None | Unset):
            uninstalled_names (list[str] | None | Unset):
            data_removed (bool | None | Unset): Operator's checkbox state at uninstall time. For the actual outcome, see
                data_tables_dropped + data_tables_drop_failed.
            data_tables_dropped (list[str] | None | Unset): Tables actually dropped (via manifest's
                databases.postgres.tables[]). Empty when remove_data=False or plugin declared no tables. Idempotent — re-
                uninstall produces the same list.
            data_tables_drop_failed (list[PluginUninstallResponseDataTablesDropFailedType0Item] | None | Unset): Per-table
                DROP failures with reason strings. Empty on success. Operators use this to manually clean up tables the platform
                couldn't drop.
            migrations_run (list[str] | None | Unset): *_down.sql migration files executed (plugin author's intended
                cleanup). Defense-in-depth manifest-table drop in data_tables_dropped runs in addition.
            references_removed (bool | None | Unset): Operator's checkbox state at uninstall time. For the actual cleanup
                outcome, see references_cleanup.
            references_cleanup (None | PluginUninstallResponseReferencesCleanupType0 | Unset): Per-kind cleanup outcomes
                when remove_references=true. Shape: {annotations_deleted: [{id, title}], shares_deleted: [{id, label}],
                fusions_repointed: [{id, name}], alerts_left_alone: [{id, name}], failed: [{kind, id, error}]}. Null when
                operator didn't opt in.
            restart_required (bool | None | Unset):
            note (None | str | Unset):
    """

    status: str
    dependents: list[UninstallDependent] | None | Unset = UNSET
    uninstalled: list[str] | None | Unset = UNSET
    uninstalled_names: list[str] | None | Unset = UNSET
    data_removed: bool | None | Unset = UNSET
    data_tables_dropped: list[str] | None | Unset = UNSET
    data_tables_drop_failed: list[PluginUninstallResponseDataTablesDropFailedType0Item] | None | Unset = UNSET
    migrations_run: list[str] | None | Unset = UNSET
    references_removed: bool | None | Unset = UNSET
    references_cleanup: None | PluginUninstallResponseReferencesCleanupType0 | Unset = UNSET
    restart_required: bool | None | Unset = UNSET
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.plugin_uninstall_response_references_cleanup_type_0 import (
            PluginUninstallResponseReferencesCleanupType0,
        )

        status = self.status

        dependents: list[dict[str, Any]] | None | Unset
        if isinstance(self.dependents, Unset):
            dependents = UNSET
        elif isinstance(self.dependents, list):
            dependents = []
            for dependents_type_0_item_data in self.dependents:
                dependents_type_0_item = dependents_type_0_item_data.to_dict()
                dependents.append(dependents_type_0_item)

        else:
            dependents = self.dependents

        uninstalled: list[str] | None | Unset
        if isinstance(self.uninstalled, Unset):
            uninstalled = UNSET
        elif isinstance(self.uninstalled, list):
            uninstalled = self.uninstalled

        else:
            uninstalled = self.uninstalled

        uninstalled_names: list[str] | None | Unset
        if isinstance(self.uninstalled_names, Unset):
            uninstalled_names = UNSET
        elif isinstance(self.uninstalled_names, list):
            uninstalled_names = self.uninstalled_names

        else:
            uninstalled_names = self.uninstalled_names

        data_removed: bool | None | Unset
        if isinstance(self.data_removed, Unset):
            data_removed = UNSET
        else:
            data_removed = self.data_removed

        data_tables_dropped: list[str] | None | Unset
        if isinstance(self.data_tables_dropped, Unset):
            data_tables_dropped = UNSET
        elif isinstance(self.data_tables_dropped, list):
            data_tables_dropped = self.data_tables_dropped

        else:
            data_tables_dropped = self.data_tables_dropped

        data_tables_drop_failed: list[dict[str, Any]] | None | Unset
        if isinstance(self.data_tables_drop_failed, Unset):
            data_tables_drop_failed = UNSET
        elif isinstance(self.data_tables_drop_failed, list):
            data_tables_drop_failed = []
            for data_tables_drop_failed_type_0_item_data in self.data_tables_drop_failed:
                data_tables_drop_failed_type_0_item = data_tables_drop_failed_type_0_item_data.to_dict()
                data_tables_drop_failed.append(data_tables_drop_failed_type_0_item)

        else:
            data_tables_drop_failed = self.data_tables_drop_failed

        migrations_run: list[str] | None | Unset
        if isinstance(self.migrations_run, Unset):
            migrations_run = UNSET
        elif isinstance(self.migrations_run, list):
            migrations_run = self.migrations_run

        else:
            migrations_run = self.migrations_run

        references_removed: bool | None | Unset
        if isinstance(self.references_removed, Unset):
            references_removed = UNSET
        else:
            references_removed = self.references_removed

        references_cleanup: dict[str, Any] | None | Unset
        if isinstance(self.references_cleanup, Unset):
            references_cleanup = UNSET
        elif isinstance(self.references_cleanup, PluginUninstallResponseReferencesCleanupType0):
            references_cleanup = self.references_cleanup.to_dict()
        else:
            references_cleanup = self.references_cleanup

        restart_required: bool | None | Unset
        if isinstance(self.restart_required, Unset):
            restart_required = UNSET
        else:
            restart_required = self.restart_required

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
            }
        )
        if dependents is not UNSET:
            field_dict["dependents"] = dependents
        if uninstalled is not UNSET:
            field_dict["uninstalled"] = uninstalled
        if uninstalled_names is not UNSET:
            field_dict["uninstalled_names"] = uninstalled_names
        if data_removed is not UNSET:
            field_dict["data_removed"] = data_removed
        if data_tables_dropped is not UNSET:
            field_dict["data_tables_dropped"] = data_tables_dropped
        if data_tables_drop_failed is not UNSET:
            field_dict["data_tables_drop_failed"] = data_tables_drop_failed
        if migrations_run is not UNSET:
            field_dict["migrations_run"] = migrations_run
        if references_removed is not UNSET:
            field_dict["references_removed"] = references_removed
        if references_cleanup is not UNSET:
            field_dict["references_cleanup"] = references_cleanup
        if restart_required is not UNSET:
            field_dict["restart_required"] = restart_required
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.plugin_uninstall_response_data_tables_drop_failed_type_0_item import (
            PluginUninstallResponseDataTablesDropFailedType0Item,
        )
        from ..models.plugin_uninstall_response_references_cleanup_type_0 import (
            PluginUninstallResponseReferencesCleanupType0,
        )
        from ..models.uninstall_dependent import UninstallDependent

        d = dict(src_dict)
        status = d.pop("status")

        def _parse_dependents(data: object) -> list[UninstallDependent] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                dependents_type_0 = []
                _dependents_type_0 = data
                for dependents_type_0_item_data in _dependents_type_0:
                    dependents_type_0_item = UninstallDependent.from_dict(dependents_type_0_item_data)

                    dependents_type_0.append(dependents_type_0_item)

                return dependents_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[UninstallDependent] | None | Unset, data)

        dependents = _parse_dependents(d.pop("dependents", UNSET))

        def _parse_uninstalled(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                uninstalled_type_0 = cast(list[str], data)

                return uninstalled_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        uninstalled = _parse_uninstalled(d.pop("uninstalled", UNSET))

        def _parse_uninstalled_names(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                uninstalled_names_type_0 = cast(list[str], data)

                return uninstalled_names_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        uninstalled_names = _parse_uninstalled_names(d.pop("uninstalled_names", UNSET))

        def _parse_data_removed(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        data_removed = _parse_data_removed(d.pop("data_removed", UNSET))

        def _parse_data_tables_dropped(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                data_tables_dropped_type_0 = cast(list[str], data)

                return data_tables_dropped_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        data_tables_dropped = _parse_data_tables_dropped(d.pop("data_tables_dropped", UNSET))

        def _parse_data_tables_drop_failed(
            data: object,
        ) -> list[PluginUninstallResponseDataTablesDropFailedType0Item] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                data_tables_drop_failed_type_0 = []
                _data_tables_drop_failed_type_0 = data
                for data_tables_drop_failed_type_0_item_data in _data_tables_drop_failed_type_0:
                    data_tables_drop_failed_type_0_item = (
                        PluginUninstallResponseDataTablesDropFailedType0Item.from_dict(
                            data_tables_drop_failed_type_0_item_data
                        )
                    )

                    data_tables_drop_failed_type_0.append(data_tables_drop_failed_type_0_item)

                return data_tables_drop_failed_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[PluginUninstallResponseDataTablesDropFailedType0Item] | None | Unset, data)

        data_tables_drop_failed = _parse_data_tables_drop_failed(d.pop("data_tables_drop_failed", UNSET))

        def _parse_migrations_run(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                migrations_run_type_0 = cast(list[str], data)

                return migrations_run_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        migrations_run = _parse_migrations_run(d.pop("migrations_run", UNSET))

        def _parse_references_removed(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        references_removed = _parse_references_removed(d.pop("references_removed", UNSET))

        def _parse_references_cleanup(data: object) -> None | PluginUninstallResponseReferencesCleanupType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                references_cleanup_type_0 = PluginUninstallResponseReferencesCleanupType0.from_dict(data)

                return references_cleanup_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PluginUninstallResponseReferencesCleanupType0 | Unset, data)

        references_cleanup = _parse_references_cleanup(d.pop("references_cleanup", UNSET))

        def _parse_restart_required(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        restart_required = _parse_restart_required(d.pop("restart_required", UNSET))

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        plugin_uninstall_response = cls(
            status=status,
            dependents=dependents,
            uninstalled=uninstalled,
            uninstalled_names=uninstalled_names,
            data_removed=data_removed,
            data_tables_dropped=data_tables_dropped,
            data_tables_drop_failed=data_tables_drop_failed,
            migrations_run=migrations_run,
            references_removed=references_removed,
            references_cleanup=references_cleanup,
            restart_required=restart_required,
            note=note,
        )

        plugin_uninstall_response.additional_properties = d
        return plugin_uninstall_response

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
