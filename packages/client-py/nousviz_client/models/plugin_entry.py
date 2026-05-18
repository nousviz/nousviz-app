from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.frontend_block import FrontendBlock
    from ..models.load_status import LoadStatus
    from ..models.update_status import UpdateStatus


T = TypeVar("T", bound="PluginEntry")


@_attrs_define
class PluginEntry:
    """Single plugin entry from /plugins or /plugins/{id}.

    Carries the consistent envelope (id, version, display_name, status)
    plus any number of plugin-author-defined fields (dashboards,
    datasets, actions, settings, capabilities, …). The `extra='allow'`
    config is intentional — plugin manifests are open-ended.

        Attributes:
            name (None | str | Unset): Plugin slug (matches the directory name).
            display_name (None | str | Unset):
            version (None | str | Unset):
            description (None | str | Unset):
            author (None | str | Unset):
            update_status (None | Unset | UpdateStatus):
            frontend (FrontendBlock | None | Unset):
            load_status (LoadStatus | None | Unset):
    """

    name: None | str | Unset = UNSET
    display_name: None | str | Unset = UNSET
    version: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    author: None | str | Unset = UNSET
    update_status: None | Unset | UpdateStatus = UNSET
    frontend: FrontendBlock | None | Unset = UNSET
    load_status: LoadStatus | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.frontend_block import FrontendBlock
        from ..models.load_status import LoadStatus
        from ..models.update_status import UpdateStatus

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        display_name: None | str | Unset
        if isinstance(self.display_name, Unset):
            display_name = UNSET
        else:
            display_name = self.display_name

        version: None | str | Unset
        if isinstance(self.version, Unset):
            version = UNSET
        else:
            version = self.version

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        author: None | str | Unset
        if isinstance(self.author, Unset):
            author = UNSET
        else:
            author = self.author

        update_status: dict[str, Any] | None | Unset
        if isinstance(self.update_status, Unset):
            update_status = UNSET
        elif isinstance(self.update_status, UpdateStatus):
            update_status = self.update_status.to_dict()
        else:
            update_status = self.update_status

        frontend: dict[str, Any] | None | Unset
        if isinstance(self.frontend, Unset):
            frontend = UNSET
        elif isinstance(self.frontend, FrontendBlock):
            frontend = self.frontend.to_dict()
        else:
            frontend = self.frontend

        load_status: dict[str, Any] | None | Unset
        if isinstance(self.load_status, Unset):
            load_status = UNSET
        elif isinstance(self.load_status, LoadStatus):
            load_status = self.load_status.to_dict()
        else:
            load_status = self.load_status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if display_name is not UNSET:
            field_dict["display_name"] = display_name
        if version is not UNSET:
            field_dict["version"] = version
        if description is not UNSET:
            field_dict["description"] = description
        if author is not UNSET:
            field_dict["author"] = author
        if update_status is not UNSET:
            field_dict["update_status"] = update_status
        if frontend is not UNSET:
            field_dict["frontend"] = frontend
        if load_status is not UNSET:
            field_dict["load_status"] = load_status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.frontend_block import FrontendBlock
        from ..models.load_status import LoadStatus
        from ..models.update_status import UpdateStatus

        d = dict(src_dict)

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_display_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        display_name = _parse_display_name(d.pop("display_name", UNSET))

        def _parse_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        version = _parse_version(d.pop("version", UNSET))

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_author(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        author = _parse_author(d.pop("author", UNSET))

        def _parse_update_status(data: object) -> None | Unset | UpdateStatus:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                update_status_type_0 = UpdateStatus.from_dict(data)

                return update_status_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UpdateStatus, data)

        update_status = _parse_update_status(d.pop("update_status", UNSET))

        def _parse_frontend(data: object) -> FrontendBlock | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                frontend_type_0 = FrontendBlock.from_dict(data)

                return frontend_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(FrontendBlock | None | Unset, data)

        frontend = _parse_frontend(d.pop("frontend", UNSET))

        def _parse_load_status(data: object) -> LoadStatus | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                load_status_type_0 = LoadStatus.from_dict(data)

                return load_status_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(LoadStatus | None | Unset, data)

        load_status = _parse_load_status(d.pop("load_status", UNSET))

        plugin_entry = cls(
            name=name,
            display_name=display_name,
            version=version,
            description=description,
            author=author,
            update_status=update_status,
            frontend=frontend,
            load_status=load_status,
        )

        plugin_entry.additional_properties = d
        return plugin_entry

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
