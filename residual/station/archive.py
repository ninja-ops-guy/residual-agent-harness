"""Confined runtime extraction into a private, disposable directory."""
from __future__ import annotations

import ntpath
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile
import zipfile

from residual.core import ContractError


def require_data_filter():
    # These patch floors include the June 2025 extraction-filter security fixes.
    # Capability alone is insufficient: older implementations also expose it.
    version = sys.version_info[:3]
    minimum = {(3, 11): (3, 11, 13), (3, 12): (3, 12, 11), (3, 13): (3, 13, 4)}
    if (version < minimum.get(version[:2], (3, 14, 0))
            or not callable(getattr(tarfile, "data_filter", None))):
        raise ContractError("Runtime extraction requires a patched Python with tarfile.data_filter: "
                            "3.11.13+, 3.12.11+, 3.13.4+, or 3.14+; no unfiltered fallback")


def member_path(name: str, root: Path) -> Path:
    # Treat Windows spellings consistently even on POSIX qualification hosts.
    if not name or "\\" in name or ":" in name or ntpath.splitdrive(name)[0]:
        raise ContractError("Unsafe runtime archive member")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ContractError("Unsafe runtime archive member")
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ContractError("Unsafe runtime archive member")
    return target


def logical_link_target(member: tarfile.TarInfo) -> PurePosixPath:
    """Resolve a TAR link in the logical runtime namespace.

    Safety must survive staging-directory relocation: an archive link is rejected
    if lexical normalization would ever climb above the logical runtime root,
    even when the physical staging path could make it resolve back inside before
    promotion.
    """
    target = member.linkname
    if not target or "\\" in target or ":" in target or ntpath.splitdrive(target)[0]:
        raise ContractError("Unsafe runtime archive link target")
    target_path = PurePosixPath(target)
    if target_path.is_absolute():
        raise ContractError("Unsafe runtime archive link target")

    parts = list(PurePosixPath(member.name).parent.parts) if member.issym() else []
    parts.extend(target_path.parts)
    normalized = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not normalized:
                raise ContractError("Unsafe runtime archive link target")
            normalized.pop()
            continue
        normalized.append(part)
    if not normalized:
        raise ContractError("Unsafe runtime archive link target")
    return PurePosixPath(*normalized)


def validate_link(member: tarfile.TarInfo, root: Path):
    logical = logical_link_target(member)
    target = root.joinpath(*logical.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ContractError("Unsafe runtime archive link target")


def extract_tar(archive: Path, root: Path):
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            member_path(member.name, root)
            if member.issym() or member.islnk():
                validate_link(member, root)
            elif not (member.isfile() or member.isdir()):
                raise ContractError("Unsupported runtime archive member type")

        def validated_data_filter(member, destination):
            # Repeat with the current tree to catch chains and duplicate members
            # that change the meaning of a previously inspected relative target.
            member_path(member.name, root)
            if member.issym() or member.islnk():
                validate_link(member, root)
            return tarfile.data_filter(member, destination)

        source.extractall(root, members=members, filter=validated_data_filter)


def extract_zip(archive: Path, root: Path):
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            member_path(member.filename, root)
            kind = stat.S_IFMT(member.external_attr >> 16)
            # ZIP link targets cannot be represented by zipfile's extraction API.
            # Reject link/special metadata explicitly instead of reinterpreting it.
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ContractError("Unsupported runtime ZIP member type")
        source.extractall(root)


def validate_tree(root: Path):
    canonical = root.resolve()
    inodes = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            info = path.lstat()
            if not path.resolve().is_relative_to(canonical):
                raise ContractError("Runtime extraction escaped its staging root")
            if stat.S_ISREG(info.st_mode):
                key = (info.st_dev, info.st_ino)
                count, _ = inodes.get(key, (0, info.st_nlink))
                inodes[key] = (count + 1, info.st_nlink)
            elif not (stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)):
                raise ContractError("Unsupported extracted runtime file type")
    if any(count != links for count, links in inodes.values()):
        raise ContractError("Runtime extraction created an external hardlink")
