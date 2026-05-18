from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="GitSettingsGetResponse")


@_attrs_define
class GitSettingsGetResponse:
    """GET /api/settings/git — boolean status + masked token preview.

    Never exposes the full token. The `github_token_preview` field is
    `<first8>...<last4>` for tokens longer than 12 chars, or '••••'
    when only short/redacted tokens are stored.

        Attributes:
            github_token_set (bool): True iff GITHUB_TOKEN is set in the environment.
            github_token_preview (str): Masked preview of the token. Empty string when no token is set.
    """

    github_token_set: bool
    github_token_preview: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        github_token_set = self.github_token_set

        github_token_preview = self.github_token_preview

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "github_token_set": github_token_set,
                "github_token_preview": github_token_preview,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        github_token_set = d.pop("github_token_set")

        github_token_preview = d.pop("github_token_preview")

        git_settings_get_response = cls(
            github_token_set=github_token_set,
            github_token_preview=github_token_preview,
        )

        git_settings_get_response.additional_properties = d
        return git_settings_get_response

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
