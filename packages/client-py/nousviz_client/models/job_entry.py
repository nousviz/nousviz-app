from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.job_scheduler_state import JobSchedulerState


T = TypeVar("T", bound="JobEntry")


@_attrs_define
class JobEntry:
    """Single row in /api/jobs response — one schedulable job.

    Plugin sync jobs carry the additional fields `manifest_schedule`,
    `override`, and `scheduler` (B150 — surfacing the v0.9.3 scheduler
    state to the operator UI). Core jobs (alerts-runner, health-monitor)
    omit those.

        Attributes:
            id (str): Job slug, e.g. 'starter-plugin-sync', 'alerts-runner'.
            name (str):
            description (str):
            owner (str): 'Core' for built-in jobs, plugin display name otherwise.
            command (str):
            recommended_schedule (str): Cron expression suggested for this job.
            status (str): 'healthy' | 'stale' | 'never' | etc.
            cron_active (bool): True iff a cron entry was found scheduling this job.
            recommended_label (None | str | Unset): Human-readable label for the cron.
            last_run (None | str | Unset):
            last_run_label (None | str | Unset):
            cron_source (None | str | Unset): 'pm2' | 'crontab' | 'manifest' | 'override' | None.
            next_run_at (None | str | Unset):
            manifest_schedule (None | str | Unset): Cron from plugin.yaml. Plugin sync jobs only.
            override (bool | None | Unset): True iff a per-plugin schedule override is set (B148). Plugin sync jobs only.
            scheduler (JobSchedulerState | None | Unset): v0.9.3 scheduler state for plugin sync jobs. Null for core jobs.
    """

    id: str
    name: str
    description: str
    owner: str
    command: str
    recommended_schedule: str
    status: str
    cron_active: bool
    recommended_label: None | str | Unset = UNSET
    last_run: None | str | Unset = UNSET
    last_run_label: None | str | Unset = UNSET
    cron_source: None | str | Unset = UNSET
    next_run_at: None | str | Unset = UNSET
    manifest_schedule: None | str | Unset = UNSET
    override: bool | None | Unset = UNSET
    scheduler: JobSchedulerState | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.job_scheduler_state import JobSchedulerState

        id = self.id

        name = self.name

        description = self.description

        owner = self.owner

        command = self.command

        recommended_schedule = self.recommended_schedule

        status = self.status

        cron_active = self.cron_active

        recommended_label: None | str | Unset
        if isinstance(self.recommended_label, Unset):
            recommended_label = UNSET
        else:
            recommended_label = self.recommended_label

        last_run: None | str | Unset
        if isinstance(self.last_run, Unset):
            last_run = UNSET
        else:
            last_run = self.last_run

        last_run_label: None | str | Unset
        if isinstance(self.last_run_label, Unset):
            last_run_label = UNSET
        else:
            last_run_label = self.last_run_label

        cron_source: None | str | Unset
        if isinstance(self.cron_source, Unset):
            cron_source = UNSET
        else:
            cron_source = self.cron_source

        next_run_at: None | str | Unset
        if isinstance(self.next_run_at, Unset):
            next_run_at = UNSET
        else:
            next_run_at = self.next_run_at

        manifest_schedule: None | str | Unset
        if isinstance(self.manifest_schedule, Unset):
            manifest_schedule = UNSET
        else:
            manifest_schedule = self.manifest_schedule

        override: bool | None | Unset
        if isinstance(self.override, Unset):
            override = UNSET
        else:
            override = self.override

        scheduler: dict[str, Any] | None | Unset
        if isinstance(self.scheduler, Unset):
            scheduler = UNSET
        elif isinstance(self.scheduler, JobSchedulerState):
            scheduler = self.scheduler.to_dict()
        else:
            scheduler = self.scheduler

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "description": description,
                "owner": owner,
                "command": command,
                "recommended_schedule": recommended_schedule,
                "status": status,
                "cron_active": cron_active,
            }
        )
        if recommended_label is not UNSET:
            field_dict["recommended_label"] = recommended_label
        if last_run is not UNSET:
            field_dict["last_run"] = last_run
        if last_run_label is not UNSET:
            field_dict["last_run_label"] = last_run_label
        if cron_source is not UNSET:
            field_dict["cron_source"] = cron_source
        if next_run_at is not UNSET:
            field_dict["next_run_at"] = next_run_at
        if manifest_schedule is not UNSET:
            field_dict["manifest_schedule"] = manifest_schedule
        if override is not UNSET:
            field_dict["override"] = override
        if scheduler is not UNSET:
            field_dict["scheduler"] = scheduler

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.job_scheduler_state import JobSchedulerState

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        description = d.pop("description")

        owner = d.pop("owner")

        command = d.pop("command")

        recommended_schedule = d.pop("recommended_schedule")

        status = d.pop("status")

        cron_active = d.pop("cron_active")

        def _parse_recommended_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        recommended_label = _parse_recommended_label(d.pop("recommended_label", UNSET))

        def _parse_last_run(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_run = _parse_last_run(d.pop("last_run", UNSET))

        def _parse_last_run_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_run_label = _parse_last_run_label(d.pop("last_run_label", UNSET))

        def _parse_cron_source(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        cron_source = _parse_cron_source(d.pop("cron_source", UNSET))

        def _parse_next_run_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        next_run_at = _parse_next_run_at(d.pop("next_run_at", UNSET))

        def _parse_manifest_schedule(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        manifest_schedule = _parse_manifest_schedule(d.pop("manifest_schedule", UNSET))

        def _parse_override(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        override = _parse_override(d.pop("override", UNSET))

        def _parse_scheduler(data: object) -> JobSchedulerState | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                scheduler_type_0 = JobSchedulerState.from_dict(data)

                return scheduler_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(JobSchedulerState | None | Unset, data)

        scheduler = _parse_scheduler(d.pop("scheduler", UNSET))

        job_entry = cls(
            id=id,
            name=name,
            description=description,
            owner=owner,
            command=command,
            recommended_schedule=recommended_schedule,
            status=status,
            cron_active=cron_active,
            recommended_label=recommended_label,
            last_run=last_run,
            last_run_label=last_run_label,
            cron_source=cron_source,
            next_run_at=next_run_at,
            manifest_schedule=manifest_schedule,
            override=override,
            scheduler=scheduler,
        )

        job_entry.additional_properties = d
        return job_entry

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
