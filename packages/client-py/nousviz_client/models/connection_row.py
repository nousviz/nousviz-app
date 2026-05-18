from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.connection_row_config import ConnectionRowConfig
    from ..models.connection_row_health_history_type_0_item import ConnectionRowHealthHistoryType0Item


T = TypeVar("T", bound="ConnectionRow")


@_attrs_define
class ConnectionRow:
    """A single connections row.

    `config` is the JSONB blob with the password masked as '••••••••'.
    Plugin-managed connections have name='plugin:<slug>' and store
    credentials in the credentials table instead of in config.

        Attributes:
            id (str):
            name (str):
            type_ (str): 'postgres' | 'mysql' | 'clickhouse'.
            config (ConnectionRowConfig): Connection config. The 'password' field is replaced with '••••••••' when set.
            is_default (bool | None | Unset):
            is_active (bool | None | Unset):
            description (None | str | Unset):
            tags (list[str] | None | Unset):
            created_by (None | str | Unset):
            created_at (None | str | Unset):
            updated_at (None | str | Unset):
            last_health_check (None | str | Unset):
            health_history (list[ConnectionRowHealthHistoryType0Item] | None | Unset):
    """

    id: str
    name: str
    type_: str
    config: ConnectionRowConfig
    is_default: bool | None | Unset = UNSET
    is_active: bool | None | Unset = UNSET
    description: None | str | Unset = UNSET
    tags: list[str] | None | Unset = UNSET
    created_by: None | str | Unset = UNSET
    created_at: None | str | Unset = UNSET
    updated_at: None | str | Unset = UNSET
    last_health_check: None | str | Unset = UNSET
    health_history: list[ConnectionRowHealthHistoryType0Item] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        type_ = self.type_

        config = self.config.to_dict()

        is_default: bool | None | Unset
        if isinstance(self.is_default, Unset):
            is_default = UNSET
        else:
            is_default = self.is_default

        is_active: bool | None | Unset
        if isinstance(self.is_active, Unset):
            is_active = UNSET
        else:
            is_active = self.is_active

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        tags: list[str] | None | Unset
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, list):
            tags = self.tags

        else:
            tags = self.tags

        created_by: None | str | Unset
        if isinstance(self.created_by, Unset):
            created_by = UNSET
        else:
            created_by = self.created_by

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = self.updated_at

        last_health_check: None | str | Unset
        if isinstance(self.last_health_check, Unset):
            last_health_check = UNSET
        else:
            last_health_check = self.last_health_check

        health_history: list[dict[str, Any]] | None | Unset
        if isinstance(self.health_history, Unset):
            health_history = UNSET
        elif isinstance(self.health_history, list):
            health_history = []
            for health_history_type_0_item_data in self.health_history:
                health_history_type_0_item = health_history_type_0_item_data.to_dict()
                health_history.append(health_history_type_0_item)

        else:
            health_history = self.health_history

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "type": type_,
                "config": config,
            }
        )
        if is_default is not UNSET:
            field_dict["is_default"] = is_default
        if is_active is not UNSET:
            field_dict["is_active"] = is_active
        if description is not UNSET:
            field_dict["description"] = description
        if tags is not UNSET:
            field_dict["tags"] = tags
        if created_by is not UNSET:
            field_dict["created_by"] = created_by
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if last_health_check is not UNSET:
            field_dict["last_health_check"] = last_health_check
        if health_history is not UNSET:
            field_dict["health_history"] = health_history

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.connection_row_config import ConnectionRowConfig
        from ..models.connection_row_health_history_type_0_item import ConnectionRowHealthHistoryType0Item

        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        type_ = d.pop("type")

        config = ConnectionRowConfig.from_dict(d.pop("config"))

        def _parse_is_default(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        is_default = _parse_is_default(d.pop("is_default", UNSET))

        def _parse_is_active(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        is_active = _parse_is_active(d.pop("is_active", UNSET))

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_tags(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                tags_type_0 = cast(list[str], data)

                return tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        tags = _parse_tags(d.pop("tags", UNSET))

        def _parse_created_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_by = _parse_created_by(d.pop("created_by", UNSET))

        def _parse_created_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        def _parse_updated_at(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_at = _parse_updated_at(d.pop("updated_at", UNSET))

        def _parse_last_health_check(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_health_check = _parse_last_health_check(d.pop("last_health_check", UNSET))

        def _parse_health_history(data: object) -> list[ConnectionRowHealthHistoryType0Item] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                health_history_type_0 = []
                _health_history_type_0 = data
                for health_history_type_0_item_data in _health_history_type_0:
                    health_history_type_0_item = ConnectionRowHealthHistoryType0Item.from_dict(
                        health_history_type_0_item_data
                    )

                    health_history_type_0.append(health_history_type_0_item)

                return health_history_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[ConnectionRowHealthHistoryType0Item] | None | Unset, data)

        health_history = _parse_health_history(d.pop("health_history", UNSET))

        connection_row = cls(
            id=id,
            name=name,
            type_=type_,
            config=config,
            is_default=is_default,
            is_active=is_active,
            description=description,
            tags=tags,
            created_by=created_by,
            created_at=created_at,
            updated_at=updated_at,
            last_health_check=last_health_check,
            health_history=health_history,
        )

        connection_row.additional_properties = d
        return connection_row

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
