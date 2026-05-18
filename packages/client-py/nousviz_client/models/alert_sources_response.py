from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.alert_source_entry import AlertSourceEntry


T = TypeVar("T", bound="AlertSourcesResponse")


@_attrs_define
class AlertSourcesResponse:
    """GET /api/alerts/sources — grouped by origin (postgres / connections / plugins).

    Attributes:
        postgres (list[AlertSourceEntry]):
        connections (list[AlertSourceEntry]):
        plugins (list[AlertSourceEntry]):
    """

    postgres: list[AlertSourceEntry]
    connections: list[AlertSourceEntry]
    plugins: list[AlertSourceEntry]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        postgres = []
        for postgres_item_data in self.postgres:
            postgres_item = postgres_item_data.to_dict()
            postgres.append(postgres_item)

        connections = []
        for connections_item_data in self.connections:
            connections_item = connections_item_data.to_dict()
            connections.append(connections_item)

        plugins = []
        for plugins_item_data in self.plugins:
            plugins_item = plugins_item_data.to_dict()
            plugins.append(plugins_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "postgres": postgres,
                "connections": connections,
                "plugins": plugins,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.alert_source_entry import AlertSourceEntry

        d = dict(src_dict)
        postgres = []
        _postgres = d.pop("postgres")
        for postgres_item_data in _postgres:
            postgres_item = AlertSourceEntry.from_dict(postgres_item_data)

            postgres.append(postgres_item)

        connections = []
        _connections = d.pop("connections")
        for connections_item_data in _connections:
            connections_item = AlertSourceEntry.from_dict(connections_item_data)

            connections.append(connections_item)

        plugins = []
        _plugins = d.pop("plugins")
        for plugins_item_data in _plugins:
            plugins_item = AlertSourceEntry.from_dict(plugins_item_data)

            plugins.append(plugins_item)

        alert_sources_response = cls(
            postgres=postgres,
            connections=connections,
            plugins=plugins,
        )

        alert_sources_response.additional_properties = d
        return alert_sources_response

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
