from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PluginUpdateResponse")


@_attrs_define
class PluginUpdateResponse:
    """POST /api/plugins/{id}/update — atomic-swap update result (B145).

    Attributes:
        plugin_id (str):
        status (str | Unset): Always 'updated' on success. Default: 'updated'.
        from_version (None | str | Unset):
        to_version (None | str | Unset):
        resolved_tag (None | str | Unset):
        source_class (None | str | Unset):
        source_url (None | str | Unset):
        migrations_applied (list[str] | None | Unset):
        note (None | str | Unset):
    """

    plugin_id: str
    status: str | Unset = "updated"
    from_version: None | str | Unset = UNSET
    to_version: None | str | Unset = UNSET
    resolved_tag: None | str | Unset = UNSET
    source_class: None | str | Unset = UNSET
    source_url: None | str | Unset = UNSET
    migrations_applied: list[str] | None | Unset = UNSET
    note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_id = self.plugin_id

        status = self.status

        from_version: None | str | Unset
        if isinstance(self.from_version, Unset):
            from_version = UNSET
        else:
            from_version = self.from_version

        to_version: None | str | Unset
        if isinstance(self.to_version, Unset):
            to_version = UNSET
        else:
            to_version = self.to_version

        resolved_tag: None | str | Unset
        if isinstance(self.resolved_tag, Unset):
            resolved_tag = UNSET
        else:
            resolved_tag = self.resolved_tag

        source_class: None | str | Unset
        if isinstance(self.source_class, Unset):
            source_class = UNSET
        else:
            source_class = self.source_class

        source_url: None | str | Unset
        if isinstance(self.source_url, Unset):
            source_url = UNSET
        else:
            source_url = self.source_url

        migrations_applied: list[str] | None | Unset
        if isinstance(self.migrations_applied, Unset):
            migrations_applied = UNSET
        elif isinstance(self.migrations_applied, list):
            migrations_applied = self.migrations_applied

        else:
            migrations_applied = self.migrations_applied

        note: None | str | Unset
        if isinstance(self.note, Unset):
            note = UNSET
        else:
            note = self.note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_id": plugin_id,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if from_version is not UNSET:
            field_dict["from_version"] = from_version
        if to_version is not UNSET:
            field_dict["to_version"] = to_version
        if resolved_tag is not UNSET:
            field_dict["resolved_tag"] = resolved_tag
        if source_class is not UNSET:
            field_dict["source_class"] = source_class
        if source_url is not UNSET:
            field_dict["source_url"] = source_url
        if migrations_applied is not UNSET:
            field_dict["migrations_applied"] = migrations_applied
        if note is not UNSET:
            field_dict["note"] = note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plugin_id = d.pop("plugin_id")

        status = d.pop("status", UNSET)

        def _parse_from_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        from_version = _parse_from_version(d.pop("from_version", UNSET))

        def _parse_to_version(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        to_version = _parse_to_version(d.pop("to_version", UNSET))

        def _parse_resolved_tag(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        resolved_tag = _parse_resolved_tag(d.pop("resolved_tag", UNSET))

        def _parse_source_class(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        source_class = _parse_source_class(d.pop("source_class", UNSET))

        def _parse_source_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        source_url = _parse_source_url(d.pop("source_url", UNSET))

        def _parse_migrations_applied(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                migrations_applied_type_0 = cast(list[str], data)

                return migrations_applied_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        migrations_applied = _parse_migrations_applied(d.pop("migrations_applied", UNSET))

        def _parse_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        note = _parse_note(d.pop("note", UNSET))

        plugin_update_response = cls(
            plugin_id=plugin_id,
            status=status,
            from_version=from_version,
            to_version=to_version,
            resolved_tag=resolved_tag,
            source_class=source_class,
            source_url=source_url,
            migrations_applied=migrations_applied,
            note=note,
        )

        plugin_update_response.additional_properties = d
        return plugin_update_response

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
