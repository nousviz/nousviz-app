from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.crontab_entry import CrontabEntry
    from ..models.job_entry import JobEntry


T = TypeVar("T", bound="JobsListResponse")


@_attrs_define
class JobsListResponse:
    """GET /api/jobs — every known scheduled job + crontab/PM2 metadata.

    `cron_source` flips between 'crontab' and 'pm2' to drive the
    frontend's "how to schedule" hint.

        Attributes:
            jobs (list[JobEntry]):
            has_crontab (bool):
            has_pm2_cron (bool):
            cron_source (str): 'pm2' | 'crontab' | 'mixed' | 'none'.
            crontab (list[CrontabEntry] | Unset): System crontab entries containing 'nousviz' — empty on PM2 deployments.
            pm2 (list[CrontabEntry] | Unset): PM2-managed processes with cron_restart — empty on crontab-only deployments.
    """

    jobs: list[JobEntry]
    has_crontab: bool
    has_pm2_cron: bool
    cron_source: str
    crontab: list[CrontabEntry] | Unset = UNSET
    pm2: list[CrontabEntry] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        jobs = []
        for jobs_item_data in self.jobs:
            jobs_item = jobs_item_data.to_dict()
            jobs.append(jobs_item)

        has_crontab = self.has_crontab

        has_pm2_cron = self.has_pm2_cron

        cron_source = self.cron_source

        crontab: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.crontab, Unset):
            crontab = []
            for crontab_item_data in self.crontab:
                crontab_item = crontab_item_data.to_dict()
                crontab.append(crontab_item)

        pm2: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.pm2, Unset):
            pm2 = []
            for pm2_item_data in self.pm2:
                pm2_item = pm2_item_data.to_dict()
                pm2.append(pm2_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "jobs": jobs,
                "has_crontab": has_crontab,
                "has_pm2_cron": has_pm2_cron,
                "cron_source": cron_source,
            }
        )
        if crontab is not UNSET:
            field_dict["crontab"] = crontab
        if pm2 is not UNSET:
            field_dict["pm2"] = pm2

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.crontab_entry import CrontabEntry
        from ..models.job_entry import JobEntry

        d = dict(src_dict)
        jobs = []
        _jobs = d.pop("jobs")
        for jobs_item_data in _jobs:
            jobs_item = JobEntry.from_dict(jobs_item_data)

            jobs.append(jobs_item)

        has_crontab = d.pop("has_crontab")

        has_pm2_cron = d.pop("has_pm2_cron")

        cron_source = d.pop("cron_source")

        _crontab = d.pop("crontab", UNSET)
        crontab: list[CrontabEntry] | Unset = UNSET
        if _crontab is not UNSET:
            crontab = []
            for crontab_item_data in _crontab:
                crontab_item = CrontabEntry.from_dict(crontab_item_data)

                crontab.append(crontab_item)

        _pm2 = d.pop("pm2", UNSET)
        pm2: list[CrontabEntry] | Unset = UNSET
        if _pm2 is not UNSET:
            pm2 = []
            for pm2_item_data in _pm2:
                pm2_item = CrontabEntry.from_dict(pm2_item_data)

                pm2.append(pm2_item)

        jobs_list_response = cls(
            jobs=jobs,
            has_crontab=has_crontab,
            has_pm2_cron=has_pm2_cron,
            cron_source=cron_source,
            crontab=crontab,
            pm2=pm2,
        )

        jobs_list_response.additional_properties = d
        return jobs_list_response

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
