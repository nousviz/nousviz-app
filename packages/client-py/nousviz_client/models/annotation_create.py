from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.annotation_create_scope_filters import AnnotationCreateScopeFilters


T = TypeVar("T", bound="AnnotationCreate")


@_attrs_define
class AnnotationCreate:
    """
    Attributes:
        title (str):
        date_start (str):
        description (None | str | Unset):
        source (str | Unset):  Default: 'manual'.
        category (str | Unset):  Default: 'note'.
        severity (str | Unset):  Default: 'info'.
        color (None | str | Unset):
        plugin_id (None | str | Unset):
        dataset (None | str | Unset):
        date_end (None | str | Unset):
        scope_filters (AnnotationCreateScopeFilters | Unset):
        tags (list[str] | Unset):
        pinned (bool | Unset):  Default: False.
        semantic_meaning (None | str | Unset):
        impact_scope (list[str] | Unset):
        semantic_score (None | str | Unset):
        semantic_note (None | str | Unset):
    """

    title: str
    date_start: str
    description: None | str | Unset = UNSET
    source: str | Unset = "manual"
    category: str | Unset = "note"
    severity: str | Unset = "info"
    color: None | str | Unset = UNSET
    plugin_id: None | str | Unset = UNSET
    dataset: None | str | Unset = UNSET
    date_end: None | str | Unset = UNSET
    scope_filters: AnnotationCreateScopeFilters | Unset = UNSET
    tags: list[str] | Unset = UNSET
    pinned: bool | Unset = False
    semantic_meaning: None | str | Unset = UNSET
    impact_scope: list[str] | Unset = UNSET
    semantic_score: None | str | Unset = UNSET
    semantic_note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        date_start = self.date_start

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        source = self.source

        category = self.category

        severity = self.severity

        color: None | str | Unset
        if isinstance(self.color, Unset):
            color = UNSET
        else:
            color = self.color

        plugin_id: None | str | Unset
        if isinstance(self.plugin_id, Unset):
            plugin_id = UNSET
        else:
            plugin_id = self.plugin_id

        dataset: None | str | Unset
        if isinstance(self.dataset, Unset):
            dataset = UNSET
        else:
            dataset = self.dataset

        date_end: None | str | Unset
        if isinstance(self.date_end, Unset):
            date_end = UNSET
        else:
            date_end = self.date_end

        scope_filters: dict[str, Any] | Unset = UNSET
        if not isinstance(self.scope_filters, Unset):
            scope_filters = self.scope_filters.to_dict()

        tags: list[str] | Unset = UNSET
        if not isinstance(self.tags, Unset):
            tags = self.tags

        pinned = self.pinned

        semantic_meaning: None | str | Unset
        if isinstance(self.semantic_meaning, Unset):
            semantic_meaning = UNSET
        else:
            semantic_meaning = self.semantic_meaning

        impact_scope: list[str] | Unset = UNSET
        if not isinstance(self.impact_scope, Unset):
            impact_scope = self.impact_scope

        semantic_score: None | str | Unset
        if isinstance(self.semantic_score, Unset):
            semantic_score = UNSET
        else:
            semantic_score = self.semantic_score

        semantic_note: None | str | Unset
        if isinstance(self.semantic_note, Unset):
            semantic_note = UNSET
        else:
            semantic_note = self.semantic_note

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "date_start": date_start,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if source is not UNSET:
            field_dict["source"] = source
        if category is not UNSET:
            field_dict["category"] = category
        if severity is not UNSET:
            field_dict["severity"] = severity
        if color is not UNSET:
            field_dict["color"] = color
        if plugin_id is not UNSET:
            field_dict["plugin_id"] = plugin_id
        if dataset is not UNSET:
            field_dict["dataset"] = dataset
        if date_end is not UNSET:
            field_dict["date_end"] = date_end
        if scope_filters is not UNSET:
            field_dict["scope_filters"] = scope_filters
        if tags is not UNSET:
            field_dict["tags"] = tags
        if pinned is not UNSET:
            field_dict["pinned"] = pinned
        if semantic_meaning is not UNSET:
            field_dict["semantic_meaning"] = semantic_meaning
        if impact_scope is not UNSET:
            field_dict["impact_scope"] = impact_scope
        if semantic_score is not UNSET:
            field_dict["semantic_score"] = semantic_score
        if semantic_note is not UNSET:
            field_dict["semantic_note"] = semantic_note

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.annotation_create_scope_filters import AnnotationCreateScopeFilters

        d = dict(src_dict)
        title = d.pop("title")

        date_start = d.pop("date_start")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        source = d.pop("source", UNSET)

        category = d.pop("category", UNSET)

        severity = d.pop("severity", UNSET)

        def _parse_color(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        color = _parse_color(d.pop("color", UNSET))

        def _parse_plugin_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        plugin_id = _parse_plugin_id(d.pop("plugin_id", UNSET))

        def _parse_dataset(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        dataset = _parse_dataset(d.pop("dataset", UNSET))

        def _parse_date_end(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        date_end = _parse_date_end(d.pop("date_end", UNSET))

        _scope_filters = d.pop("scope_filters", UNSET)
        scope_filters: AnnotationCreateScopeFilters | Unset
        if isinstance(_scope_filters, Unset):
            scope_filters = UNSET
        else:
            scope_filters = AnnotationCreateScopeFilters.from_dict(_scope_filters)

        tags = cast(list[str], d.pop("tags", UNSET))

        pinned = d.pop("pinned", UNSET)

        def _parse_semantic_meaning(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        semantic_meaning = _parse_semantic_meaning(d.pop("semantic_meaning", UNSET))

        impact_scope = cast(list[str], d.pop("impact_scope", UNSET))

        def _parse_semantic_score(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        semantic_score = _parse_semantic_score(d.pop("semantic_score", UNSET))

        def _parse_semantic_note(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        semantic_note = _parse_semantic_note(d.pop("semantic_note", UNSET))

        annotation_create = cls(
            title=title,
            date_start=date_start,
            description=description,
            source=source,
            category=category,
            severity=severity,
            color=color,
            plugin_id=plugin_id,
            dataset=dataset,
            date_end=date_end,
            scope_filters=scope_filters,
            tags=tags,
            pinned=pinned,
            semantic_meaning=semantic_meaning,
            impact_scope=impact_scope,
            semantic_score=semantic_score,
            semantic_note=semantic_note,
        )

        annotation_create.additional_properties = d
        return annotation_create

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
