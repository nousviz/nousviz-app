from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.annotation_update_scope_filters_type_0 import AnnotationUpdateScopeFiltersType0


T = TypeVar("T", bound="AnnotationUpdate")


@_attrs_define
class AnnotationUpdate:
    """
    Attributes:
        title (None | str | Unset):
        description (None | str | Unset):
        category (None | str | Unset):
        severity (None | str | Unset):
        color (None | str | Unset):
        plugin_id (None | str | Unset):
        dataset (None | str | Unset):
        date_start (None | str | Unset):
        date_end (None | str | Unset):
        scope_filters (AnnotationUpdateScopeFiltersType0 | None | Unset):
        tags (list[str] | None | Unset):
        pinned (bool | None | Unset):
        archived (bool | None | Unset):
        semantic_meaning (None | str | Unset):
        impact_scope (list[str] | None | Unset):
        semantic_score (None | str | Unset):
        semantic_note (None | str | Unset):
    """

    title: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    category: None | str | Unset = UNSET
    severity: None | str | Unset = UNSET
    color: None | str | Unset = UNSET
    plugin_id: None | str | Unset = UNSET
    dataset: None | str | Unset = UNSET
    date_start: None | str | Unset = UNSET
    date_end: None | str | Unset = UNSET
    scope_filters: AnnotationUpdateScopeFiltersType0 | None | Unset = UNSET
    tags: list[str] | None | Unset = UNSET
    pinned: bool | None | Unset = UNSET
    archived: bool | None | Unset = UNSET
    semantic_meaning: None | str | Unset = UNSET
    impact_scope: list[str] | None | Unset = UNSET
    semantic_score: None | str | Unset = UNSET
    semantic_note: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.annotation_update_scope_filters_type_0 import AnnotationUpdateScopeFiltersType0

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        category: None | str | Unset
        if isinstance(self.category, Unset):
            category = UNSET
        else:
            category = self.category

        severity: None | str | Unset
        if isinstance(self.severity, Unset):
            severity = UNSET
        else:
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

        date_start: None | str | Unset
        if isinstance(self.date_start, Unset):
            date_start = UNSET
        else:
            date_start = self.date_start

        date_end: None | str | Unset
        if isinstance(self.date_end, Unset):
            date_end = UNSET
        else:
            date_end = self.date_end

        scope_filters: dict[str, Any] | None | Unset
        if isinstance(self.scope_filters, Unset):
            scope_filters = UNSET
        elif isinstance(self.scope_filters, AnnotationUpdateScopeFiltersType0):
            scope_filters = self.scope_filters.to_dict()
        else:
            scope_filters = self.scope_filters

        tags: list[str] | None | Unset
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, list):
            tags = self.tags

        else:
            tags = self.tags

        pinned: bool | None | Unset
        if isinstance(self.pinned, Unset):
            pinned = UNSET
        else:
            pinned = self.pinned

        archived: bool | None | Unset
        if isinstance(self.archived, Unset):
            archived = UNSET
        else:
            archived = self.archived

        semantic_meaning: None | str | Unset
        if isinstance(self.semantic_meaning, Unset):
            semantic_meaning = UNSET
        else:
            semantic_meaning = self.semantic_meaning

        impact_scope: list[str] | None | Unset
        if isinstance(self.impact_scope, Unset):
            impact_scope = UNSET
        elif isinstance(self.impact_scope, list):
            impact_scope = self.impact_scope

        else:
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
        field_dict.update({})
        if title is not UNSET:
            field_dict["title"] = title
        if description is not UNSET:
            field_dict["description"] = description
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
        if date_start is not UNSET:
            field_dict["date_start"] = date_start
        if date_end is not UNSET:
            field_dict["date_end"] = date_end
        if scope_filters is not UNSET:
            field_dict["scope_filters"] = scope_filters
        if tags is not UNSET:
            field_dict["tags"] = tags
        if pinned is not UNSET:
            field_dict["pinned"] = pinned
        if archived is not UNSET:
            field_dict["archived"] = archived
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
        from ..models.annotation_update_scope_filters_type_0 import AnnotationUpdateScopeFiltersType0

        d = dict(src_dict)

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_category(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        category = _parse_category(d.pop("category", UNSET))

        def _parse_severity(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        severity = _parse_severity(d.pop("severity", UNSET))

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

        def _parse_date_start(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        date_start = _parse_date_start(d.pop("date_start", UNSET))

        def _parse_date_end(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        date_end = _parse_date_end(d.pop("date_end", UNSET))

        def _parse_scope_filters(data: object) -> AnnotationUpdateScopeFiltersType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                scope_filters_type_0 = AnnotationUpdateScopeFiltersType0.from_dict(data)

                return scope_filters_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(AnnotationUpdateScopeFiltersType0 | None | Unset, data)

        scope_filters = _parse_scope_filters(d.pop("scope_filters", UNSET))

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

        def _parse_pinned(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        pinned = _parse_pinned(d.pop("pinned", UNSET))

        def _parse_archived(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        archived = _parse_archived(d.pop("archived", UNSET))

        def _parse_semantic_meaning(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        semantic_meaning = _parse_semantic_meaning(d.pop("semantic_meaning", UNSET))

        def _parse_impact_scope(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                impact_scope_type_0 = cast(list[str], data)

                return impact_scope_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        impact_scope = _parse_impact_scope(d.pop("impact_scope", UNSET))

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

        annotation_update = cls(
            title=title,
            description=description,
            category=category,
            severity=severity,
            color=color,
            plugin_id=plugin_id,
            dataset=dataset,
            date_start=date_start,
            date_end=date_end,
            scope_filters=scope_filters,
            tags=tags,
            pinned=pinned,
            archived=archived,
            semantic_meaning=semantic_meaning,
            impact_scope=impact_scope,
            semantic_score=semantic_score,
            semantic_note=semantic_note,
        )

        annotation_update.additional_properties = d
        return annotation_update

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
