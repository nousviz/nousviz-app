from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.sync_schedule_registry import SyncScheduleRegistry


T = TypeVar("T", bound="SyncScheduleGetResponse")


@_attrs_define
class SyncScheduleGetResponse:
    """GET /api/plugins/{id}/sync-schedule — composite read used by the Settings tab.

    Attributes:
        plugin_id (str):
        source (str): 'override' | 'manifest'.
        scheduler_alive (bool): True iff the scheduler row was updated within the last 5 minutes.
        manifest_cron (None | str | Unset): Cron from plugin.yaml (sync.schedule).
        manifest_cron_display (None | str | Unset): Human label for manifest_cron, when expressible.
        override_cron (None | str | Unset):
        override_cron_display (None | str | Unset):
        effective_cron (None | str | Unset): override_cron when set, else manifest_cron.
        effective_cron_display (None | str | Unset):
        registry (None | SyncScheduleRegistry | Unset):
    """

    plugin_id: str
    source: str
    scheduler_alive: bool
    manifest_cron: None | str | Unset = UNSET
    manifest_cron_display: None | str | Unset = UNSET
    override_cron: None | str | Unset = UNSET
    override_cron_display: None | str | Unset = UNSET
    effective_cron: None | str | Unset = UNSET
    effective_cron_display: None | str | Unset = UNSET
    registry: None | SyncScheduleRegistry | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.sync_schedule_registry import SyncScheduleRegistry

        plugin_id = self.plugin_id

        source = self.source

        scheduler_alive = self.scheduler_alive

        manifest_cron: None | str | Unset
        if isinstance(self.manifest_cron, Unset):
            manifest_cron = UNSET
        else:
            manifest_cron = self.manifest_cron

        manifest_cron_display: None | str | Unset
        if isinstance(self.manifest_cron_display, Unset):
            manifest_cron_display = UNSET
        else:
            manifest_cron_display = self.manifest_cron_display

        override_cron: None | str | Unset
        if isinstance(self.override_cron, Unset):
            override_cron = UNSET
        else:
            override_cron = self.override_cron

        override_cron_display: None | str | Unset
        if isinstance(self.override_cron_display, Unset):
            override_cron_display = UNSET
        else:
            override_cron_display = self.override_cron_display

        effective_cron: None | str | Unset
        if isinstance(self.effective_cron, Unset):
            effective_cron = UNSET
        else:
            effective_cron = self.effective_cron

        effective_cron_display: None | str | Unset
        if isinstance(self.effective_cron_display, Unset):
            effective_cron_display = UNSET
        else:
            effective_cron_display = self.effective_cron_display

        registry: dict[str, Any] | None | Unset
        if isinstance(self.registry, Unset):
            registry = UNSET
        elif isinstance(self.registry, SyncScheduleRegistry):
            registry = self.registry.to_dict()
        else:
            registry = self.registry

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
                "source": source,
                "scheduler_alive": scheduler_alive,
            }
        )
        if manifest_cron is not UNSET:
            field_dict["manifest_cron"] = manifest_cron
        if manifest_cron_display is not UNSET:
            field_dict["manifest_cron_display"] = manifest_cron_display
        if override_cron is not UNSET:
            field_dict["override_cron"] = override_cron
        if override_cron_display is not UNSET:
            field_dict["override_cron_display"] = override_cron_display
        if effective_cron is not UNSET:
            field_dict["effective_cron"] = effective_cron
        if effective_cron_display is not UNSET:
            field_dict["effective_cron_display"] = effective_cron_display
        if registry is not UNSET:
            field_dict["registry"] = registry

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.sync_schedule_registry import SyncScheduleRegistry

        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        source = d.pop("source")

        scheduler_alive = d.pop("scheduler_alive")

        def _parse_manifest_cron(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        manifest_cron = _parse_manifest_cron(d.pop("manifest_cron", UNSET))

        def _parse_manifest_cron_display(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        manifest_cron_display = _parse_manifest_cron_display(d.pop("manifest_cron_display", UNSET))

        def _parse_override_cron(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        override_cron = _parse_override_cron(d.pop("override_cron", UNSET))

        def _parse_override_cron_display(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        override_cron_display = _parse_override_cron_display(d.pop("override_cron_display", UNSET))

        def _parse_effective_cron(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        effective_cron = _parse_effective_cron(d.pop("effective_cron", UNSET))

        def _parse_effective_cron_display(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        effective_cron_display = _parse_effective_cron_display(d.pop("effective_cron_display", UNSET))

        def _parse_registry(data: object) -> None | SyncScheduleRegistry | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                registry_type_0 = SyncScheduleRegistry.from_dict(data)

                return registry_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SyncScheduleRegistry | Unset, data)

        registry = _parse_registry(d.pop("registry", UNSET))

        sync_schedule_get_response = cls(
            plugin_id=plugin_id,
            source=source,
            scheduler_alive=scheduler_alive,
            manifest_cron=manifest_cron,
            manifest_cron_display=manifest_cron_display,
            override_cron=override_cron,
            override_cron_display=override_cron_display,
            effective_cron=effective_cron,
            effective_cron_display=effective_cron_display,
            registry=registry,
        )

        sync_schedule_get_response.additional_properties = d
        return sync_schedule_get_response

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
