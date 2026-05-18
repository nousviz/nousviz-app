from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.query_response_guardrails_type_0 import QueryResponseGuardrailsType0
    from ..models.query_response_rows_item import QueryResponseRowsItem


T = TypeVar("T", bound="QueryResponse")


@_attrs_define
class QueryResponse:
    """
    Attributes:
        columns (list[str]):
        types (list[str]):
        rows (list[QueryResponseRowsItem]):
        row_count (int):
        elapsed_ms (float):
        total_rows_available (int | None | Unset):
        truncated (bool | Unset):  Default: False.
        db_engine (str | Unset):  Default: 'postgres'.
        guardrails (None | QueryResponseGuardrailsType0 | Unset):
    """

    columns: list[str]
    types: list[str]
    rows: list[QueryResponseRowsItem]
    row_count: int
    elapsed_ms: float
    total_rows_available: int | None | Unset = UNSET
    truncated: bool | Unset = False
    db_engine: str | Unset = "postgres"
    guardrails: None | QueryResponseGuardrailsType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.query_response_guardrails_type_0 import QueryResponseGuardrailsType0

        columns = self.columns

        types = self.types

        rows = []
        for rows_item_data in self.rows:
            rows_item = rows_item_data.to_dict()
            rows.append(rows_item)

        row_count = self.row_count

        elapsed_ms = self.elapsed_ms

        total_rows_available: int | None | Unset
        if isinstance(self.total_rows_available, Unset):
            total_rows_available = UNSET
        else:
            total_rows_available = self.total_rows_available

        truncated = self.truncated

        db_engine = self.db_engine

        guardrails: dict[str, Any] | None | Unset
        if isinstance(self.guardrails, Unset):
            guardrails = UNSET
        elif isinstance(self.guardrails, QueryResponseGuardrailsType0):
            guardrails = self.guardrails.to_dict()
        else:
            guardrails = self.guardrails

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "columns": columns,
                "types": types,
                "rows": rows,
                "row_count": row_count,
                "elapsed_ms": elapsed_ms,
            }
        )
        if total_rows_available is not UNSET:
            field_dict["total_rows_available"] = total_rows_available
        if truncated is not UNSET:
            field_dict["truncated"] = truncated
        if db_engine is not UNSET:
            field_dict["db_engine"] = db_engine
        if guardrails is not UNSET:
            field_dict["guardrails"] = guardrails

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.query_response_guardrails_type_0 import QueryResponseGuardrailsType0
        from ..models.query_response_rows_item import QueryResponseRowsItem

        d = dict(src_dict)
        columns = cast(list[str], d.pop("columns"))

        types = cast(list[str], d.pop("types"))

        rows = []
        _rows = d.pop("rows")
        for rows_item_data in _rows:
            rows_item = QueryResponseRowsItem.from_dict(rows_item_data)

            rows.append(rows_item)

        row_count = d.pop("row_count")

        elapsed_ms = d.pop("elapsed_ms")

        def _parse_total_rows_available(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        total_rows_available = _parse_total_rows_available(d.pop("total_rows_available", UNSET))

        truncated = d.pop("truncated", UNSET)

        db_engine = d.pop("db_engine", UNSET)

        def _parse_guardrails(data: object) -> None | QueryResponseGuardrailsType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                guardrails_type_0 = QueryResponseGuardrailsType0.from_dict(data)

                return guardrails_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | QueryResponseGuardrailsType0 | Unset, data)

        guardrails = _parse_guardrails(d.pop("guardrails", UNSET))

        query_response = cls(
            columns=columns,
            types=types,
            rows=rows,
            row_count=row_count,
            elapsed_ms=elapsed_ms,
            total_rows_available=total_rows_available,
            truncated=truncated,
            db_engine=db_engine,
            guardrails=guardrails,
        )

        query_response.additional_properties = d
        return query_response

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
