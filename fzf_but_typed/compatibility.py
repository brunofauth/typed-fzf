from __future__ import annotations

import bisect
import dataclasses as dc
import subprocess as sp
import sys
import re

from typing import Self, NoReturn

_RE_SEMVER = re.compile(r'^(?P<major>\d+)\.(?P<minor>\d+).(?P<patch>\d+)\S*')

# yapf: disable
_ERROR_HEADER = (
    "The contents of this module were written module taking into consideration the man "
    "pages of fzf version={my_version!s}. You're using fzf version={your_version!s} "
)
_ERROR_OLDER = (
    "which is older than the version I used, meaning that some of the features exposed "
    "on this API wrapper may not work (they're not implemented yet in your 'fzf'). "
)
_ERROR_NEWER = (
    "which is newer than the version I used, meaning that some features from fzf that "
    "you may want to use may be absent here. "
)
_ERROR_PREVIOUSLY_SUPPORTED = (
    "In your particular case, the version you're using has been supported by a previous "
    "version of this library ({}), so, if you want, you can downgrade this package to get "
    "full compatibility, instead of updating 'fzf'; it's really up to you... "
)
_ERROR_EPILOGUE = (
    "Regardless of all this, your use case might probably be supported by this lib. I've "
    "included the aformentioned manpages in this package's repo, so, if you want to be 100% "
    " sure, you can download these manpages and run them through 'diff' with your system's "
    "manpages for fzf. See README.md for an example of how to do this."
)
# yapf: enable


@dc.dataclass(frozen=True, slots=True, kw_only=True, order=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def from_str(cls, value: str) -> Self:
        if (match := _RE_SEMVER.search(value)) is None:
            raise ValueError(f"can't parse given semver: {value}")
        return cls(major=int(match["major"]), minor=int(match["minor"]), patch=int(match["patch"]))

    def is_compatible_with(self, other: Self) -> bool:
        return self.major == other.major and self.minor == other.minor


def _get_installed_fzf_version() -> SemVer:
    result = sp.run(['fzf', '--version'], capture_output=True, text=True, check=True).stdout.strip()
    try:
        return SemVer.from_str(result)
    except ValueError as error:
        error.add_note(f"this semver was generated by running 'fzf --version'. ")
        raise


def _raise_error(
    my_version: SemVer,
    your_version: SemVer,
    previously_supported: SemVer | None = None,
) -> NoReturn:
    raise RuntimeError("".join([
        _ERROR_HEADER.format(my_version=my_version, your_version=your_version),
        _ERROR_NEWER if your_version > my_version else _ERROR_OLDER,
        _ERROR_PREVIOUSLY_SUPPORTED.format(previously_supported)
        if previously_supported is not None else "",
        _ERROR_EPILOGUE,
    ]))


def _test_compatibility(
    latest_supported: SemVer,
    found_version: SemVer,
    all_supported_versions: list[tuple[SemVer, SemVer]],
) -> NoReturn:
    index = bisect.bisect(
        all_supported_versions,
        found_version,
        key=lambda pair: pair[0],
    )

    if index == 0:
        _raise_error(latest_supported, found_version)

    if found_version.is_compatible_with(latest_supported):
        print("versions are compatible... you're fine!", file=sys.stderr)
        raise SystemExit()

    if index == len(all_supported_versions):
        _raise_error(latest_supported, found_version)

    prev_fzf_version, prev_lib_version = all_supported_versions[index - 1]
    if found_version.is_compatible_with(prev_fzf_version):
        _raise_error(latest_supported, found_version, previously_supported=prev_lib_version)

    prev_fzf_version, prev_lib_version = all_supported_versions[index]
    if found_version.is_compatible_with(prev_fzf_version):
        _raise_error(latest_supported, found_version, previously_supported=prev_lib_version)

    _raise_error(latest_supported, found_version)


def test_compatibility() -> NoReturn:
    # Keys are fzf versions; values are this package's versions
    all_supported_versions: list[tuple[SemVer, SemVer]] = [
        (SemVer(major=0, minor=42, patch=0), SemVer(major=0, minor=1, patch=0)),
        (SemVer(major=0, minor=43, patch=0), SemVer(major=0, minor=2, patch=0)),
    ]
    latest_supported_fzf = all_supported_versions[-1][0]
    found_fzf_version = _get_installed_fzf_version()
    _test_compatibility(latest_supported_fzf, found_fzf_version, all_supported_versions)


if __name__ == "__main__":
    test_compatibility()
