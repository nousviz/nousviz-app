from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.server_resources_cpu import ServerResourcesCpu
    from ..models.server_resources_disk import ServerResourcesDisk
    from ..models.server_resources_load import ServerResourcesLoad
    from ..models.server_resources_memory import ServerResourcesMemory
    from ..models.server_resources_swap import ServerResourcesSwap


T = TypeVar("T", bound="ServerResources")


@_attrs_define
class ServerResources:
    """Server-level metrics. Fields are Optional because the API runs
    on Linux production but also on macOS dev (no /proc/meminfo etc.).

        Attributes:
            cpu (None | ServerResourcesCpu | Unset):
            memory (None | ServerResourcesMemory | Unset):
            swap (None | ServerResourcesSwap | Unset):
            disk_root (None | ServerResourcesDisk | Unset):
            load (None | ServerResourcesLoad | Unset):
            uptime_seconds (int | None | Unset):
    """

    cpu: None | ServerResourcesCpu | Unset = UNSET
    memory: None | ServerResourcesMemory | Unset = UNSET
    swap: None | ServerResourcesSwap | Unset = UNSET
    disk_root: None | ServerResourcesDisk | Unset = UNSET
    load: None | ServerResourcesLoad | Unset = UNSET
    uptime_seconds: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.server_resources_cpu import ServerResourcesCpu
        from ..models.server_resources_disk import ServerResourcesDisk
        from ..models.server_resources_load import ServerResourcesLoad
        from ..models.server_resources_memory import ServerResourcesMemory
        from ..models.server_resources_swap import ServerResourcesSwap

        cpu: dict[str, Any] | None | Unset
        if isinstance(self.cpu, Unset):
            cpu = UNSET
        elif isinstance(self.cpu, ServerResourcesCpu):
            cpu = self.cpu.to_dict()
        else:
            cpu = self.cpu

        memory: dict[str, Any] | None | Unset
        if isinstance(self.memory, Unset):
            memory = UNSET
        elif isinstance(self.memory, ServerResourcesMemory):
            memory = self.memory.to_dict()
        else:
            memory = self.memory

        swap: dict[str, Any] | None | Unset
        if isinstance(self.swap, Unset):
            swap = UNSET
        elif isinstance(self.swap, ServerResourcesSwap):
            swap = self.swap.to_dict()
        else:
            swap = self.swap

        disk_root: dict[str, Any] | None | Unset
        if isinstance(self.disk_root, Unset):
            disk_root = UNSET
        elif isinstance(self.disk_root, ServerResourcesDisk):
            disk_root = self.disk_root.to_dict()
        else:
            disk_root = self.disk_root

        load: dict[str, Any] | None | Unset
        if isinstance(self.load, Unset):
            load = UNSET
        elif isinstance(self.load, ServerResourcesLoad):
            load = self.load.to_dict()
        else:
            load = self.load

        uptime_seconds: int | None | Unset
        if isinstance(self.uptime_seconds, Unset):
            uptime_seconds = UNSET
        else:
            uptime_seconds = self.uptime_seconds

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cpu is not UNSET:
            field_dict["cpu"] = cpu
        if memory is not UNSET:
            field_dict["memory"] = memory
        if swap is not UNSET:
            field_dict["swap"] = swap
        if disk_root is not UNSET:
            field_dict["disk_root"] = disk_root
        if load is not UNSET:
            field_dict["load"] = load
        if uptime_seconds is not UNSET:
            field_dict["uptime_seconds"] = uptime_seconds

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.server_resources_cpu import ServerResourcesCpu
        from ..models.server_resources_disk import ServerResourcesDisk
        from ..models.server_resources_load import ServerResourcesLoad
        from ..models.server_resources_memory import ServerResourcesMemory
        from ..models.server_resources_swap import ServerResourcesSwap

        d = dict(src_dict)

        def _parse_cpu(data: object) -> None | ServerResourcesCpu | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                cpu_type_0 = ServerResourcesCpu.from_dict(data)

                return cpu_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ServerResourcesCpu | Unset, data)

        cpu = _parse_cpu(d.pop("cpu", UNSET))

        def _parse_memory(data: object) -> None | ServerResourcesMemory | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                memory_type_0 = ServerResourcesMemory.from_dict(data)

                return memory_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ServerResourcesMemory | Unset, data)

        memory = _parse_memory(d.pop("memory", UNSET))

        def _parse_swap(data: object) -> None | ServerResourcesSwap | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                swap_type_0 = ServerResourcesSwap.from_dict(data)

                return swap_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ServerResourcesSwap | Unset, data)

        swap = _parse_swap(d.pop("swap", UNSET))

        def _parse_disk_root(data: object) -> None | ServerResourcesDisk | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                disk_root_type_0 = ServerResourcesDisk.from_dict(data)

                return disk_root_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ServerResourcesDisk | Unset, data)

        disk_root = _parse_disk_root(d.pop("disk_root", UNSET))

        def _parse_load(data: object) -> None | ServerResourcesLoad | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                load_type_0 = ServerResourcesLoad.from_dict(data)

                return load_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ServerResourcesLoad | Unset, data)

        load = _parse_load(d.pop("load", UNSET))

        def _parse_uptime_seconds(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        uptime_seconds = _parse_uptime_seconds(d.pop("uptime_seconds", UNSET))

        server_resources = cls(
            cpu=cpu,
            memory=memory,
            swap=swap,
            disk_root=disk_root,
            load=load,
            uptime_seconds=uptime_seconds,
        )

        server_resources.additional_properties = d
        return server_resources

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
