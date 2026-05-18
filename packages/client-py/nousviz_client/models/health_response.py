from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.health_response_runtime import HealthResponseRuntime
    from ..models.health_response_services import HealthResponseServices
    from ..models.ssl_block import SSLBlock
    from ..models.stats_block import StatsBlock


T = TypeVar("T", bound="HealthResponse")


@_attrs_define
class HealthResponse:
    """Top-level /health payload.

    Status is degraded when Postgres reports degraded, the SDK is
    unavailable, or critical tables are missing. Frontend `evaluateChecks`
    drives banner display from this shape.

        Attributes:
            status (str): Overall instance status. 'healthy' | 'degraded'.
            version (str): Platform version (matches /VERSION).
            startup_time (str): When this API process started, ISO-8601.
            timestamp (str): When this response was generated, ISO-8601.
            stats (StatsBlock): Aggregate counts surfaced in /health for the operator dashboard.
            services (HealthResponseServices | Unset): Per-service health blocks. The 'postgres' key always exists with
                shape {status, version?, tables?, critical_tables_present?, critical_tables_total?, missing_critical_tables?,
                drift_hint?}. Utility-plugin entries have shape {status, version?}.
            runtime (HealthResponseRuntime | Unset): Runtime check blocks. Currently contains 'sdk' with shape {status,
                version, import_error?}.
            ssl (None | SSLBlock | Unset): SSL config status. Present iff NOUSVIZ_SSL is set in the environment.
    """

    status: str
    version: str
    startup_time: str
    timestamp: str
    stats: StatsBlock
    services: HealthResponseServices | Unset = UNSET
    runtime: HealthResponseRuntime | Unset = UNSET
    ssl: None | SSLBlock | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.ssl_block import SSLBlock

        status = self.status

        version = self.version

        startup_time = self.startup_time

        timestamp = self.timestamp

        stats = self.stats.to_dict()

        services: dict[str, Any] | Unset = UNSET
        if not isinstance(self.services, Unset):
            services = self.services.to_dict()

        runtime: dict[str, Any] | Unset = UNSET
        if not isinstance(self.runtime, Unset):
            runtime = self.runtime.to_dict()

        ssl: dict[str, Any] | None | Unset
        if isinstance(self.ssl, Unset):
            ssl = UNSET
        elif isinstance(self.ssl, SSLBlock):
            ssl = self.ssl.to_dict()
        else:
            ssl = self.ssl

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "version": version,
                "startup_time": startup_time,
                "timestamp": timestamp,
                "stats": stats,
            }
        )
        if services is not UNSET:
            field_dict["services"] = services
        if runtime is not UNSET:
            field_dict["runtime"] = runtime
        if ssl is not UNSET:
            field_dict["ssl"] = ssl

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.health_response_runtime import HealthResponseRuntime
        from ..models.health_response_services import HealthResponseServices
        from ..models.ssl_block import SSLBlock
        from ..models.stats_block import StatsBlock

        d = dict(src_dict)
        status = d.pop("status")

        version = d.pop("version")

        startup_time = d.pop("startup_time")

        timestamp = d.pop("timestamp")

        stats = StatsBlock.from_dict(d.pop("stats"))

        _services = d.pop("services", UNSET)
        services: HealthResponseServices | Unset
        if isinstance(_services, Unset):
            services = UNSET
        else:
            services = HealthResponseServices.from_dict(_services)

        _runtime = d.pop("runtime", UNSET)
        runtime: HealthResponseRuntime | Unset
        if isinstance(_runtime, Unset):
            runtime = UNSET
        else:
            runtime = HealthResponseRuntime.from_dict(_runtime)

        def _parse_ssl(data: object) -> None | SSLBlock | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                ssl_type_0 = SSLBlock.from_dict(data)

                return ssl_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SSLBlock | Unset, data)

        ssl = _parse_ssl(d.pop("ssl", UNSET))

        health_response = cls(
            status=status,
            version=version,
            startup_time=startup_time,
            timestamp=timestamp,
            stats=stats,
            services=services,
            runtime=runtime,
            ssl=ssl,
        )

        health_response.additional_properties = d
        return health_response

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
