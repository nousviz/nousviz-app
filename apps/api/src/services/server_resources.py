"""
B271 (v0.9.11.13) — server-level resource metrics for /api/system/resources.

Pure shell-out wrappers around `/proc/meminfo`, `df`, `uptime`, `nproc`,
and `/proc/loadavg`. Each function returns Optional[<type>] so the API
gracefully degrades on macOS dev / non-Linux environments where /proc
doesn't exist.

No external dependencies — psutil would be cleaner but adds a wheel
the install footprint can avoid.
"""
from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nousviz.services.server_resources")


# ── Data shapes ──────────────────────────────────────────────────────


@dataclass
class MemoryStats:
    total_mb: int
    used_mb: int
    free_mb: int
    available_mb: int  # MemAvailable from /proc/meminfo (free + reclaimable buff/cache)
    buff_cache_mb: int


@dataclass
class SwapStats:
    total_mb: int
    used_mb: int
    free_mb: int


@dataclass
class DiskStats:
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    used_pct: int


@dataclass
class LoadStats:
    load_1m: float
    load_5m: float
    load_15m: float


@dataclass
class CpuInfo:
    cpu_count: int
    cpu_model: Optional[str]


@dataclass
class ServerSnapshot:
    cpu: Optional[CpuInfo]
    memory: Optional[MemoryStats]
    swap: Optional[SwapStats]
    disk_root: Optional[DiskStats]
    load: Optional[LoadStats]
    uptime_seconds: Optional[int]


# ── Shell-out helpers ────────────────────────────────────────────────


def _read_meminfo() -> Optional[dict[str, int]]:
    """Parse /proc/meminfo into a dict of kB values. None if not Linux."""
    path = Path("/proc/meminfo")
    if not path.is_file():
        return None
    try:
        out: dict[str, int] = {}
        for line in path.read_text().splitlines():
            # Lines look like: "MemTotal:        3923488 kB"
            parts = line.split()
            if len(parts) >= 2 and parts[0].endswith(":"):
                key = parts[0].rstrip(":")
                try:
                    out[key] = int(parts[1])
                except ValueError:
                    pass
        return out
    except Exception as exc:
        logger.warning(f"server_resources: /proc/meminfo read failed — {exc}")
        return None


def get_memory() -> Optional[MemoryStats]:
    """Memory in MB. None on non-Linux / unreadable /proc."""
    mi = _read_meminfo()
    if mi is None:
        return None
    total = mi.get("MemTotal", 0)
    free = mi.get("MemFree", 0)
    available = mi.get("MemAvailable", free)
    buffers = mi.get("Buffers", 0)
    cached = mi.get("Cached", 0)
    sreclaim = mi.get("SReclaimable", 0)
    buff_cache = buffers + cached + sreclaim
    used = total - free - buff_cache
    if used < 0:
        used = total - available
    return MemoryStats(
        total_mb=total // 1024,
        used_mb=max(0, used // 1024),
        free_mb=free // 1024,
        available_mb=available // 1024,
        buff_cache_mb=buff_cache // 1024,
    )


def get_swap() -> Optional[SwapStats]:
    """Swap in MB. Returns SwapStats(0,0,0) when no swap configured (linux);
    returns None on non-Linux."""
    mi = _read_meminfo()
    if mi is None:
        return None
    total = mi.get("SwapTotal", 0)
    free = mi.get("SwapFree", 0)
    used = total - free
    return SwapStats(
        total_mb=total // 1024,
        used_mb=max(0, used // 1024),
        free_mb=free // 1024,
    )


def get_disk(path: str = "/") -> Optional[DiskStats]:
    """Disk usage at the given mountpoint. Uses shutil.disk_usage which
    works on Linux + macOS."""
    try:
        usage = shutil.disk_usage(path)
        total_gb = round(usage.total / (1024 ** 3), 2)
        used_gb = round(usage.used / (1024 ** 3), 2)
        free_gb = round(usage.free / (1024 ** 3), 2)
        used_pct = int(round(usage.used / usage.total * 100)) if usage.total > 0 else 0
        return DiskStats(
            path=path,
            total_gb=total_gb,
            used_gb=used_gb,
            free_gb=free_gb,
            used_pct=used_pct,
        )
    except Exception as exc:
        logger.warning(f"server_resources: shutil.disk_usage({path!r}) failed — {exc}")
        return None


def get_load() -> Optional[LoadStats]:
    """1/5/15-minute load averages from os.getloadavg (Linux + macOS)."""
    try:
        l1, l5, l15 = os.getloadavg()
        return LoadStats(
            load_1m=round(l1, 2),
            load_5m=round(l5, 2),
            load_15m=round(l15, 2),
        )
    except Exception as exc:
        logger.warning(f"server_resources: getloadavg failed — {exc}")
        return None


def get_cpu_info() -> Optional[CpuInfo]:
    """CPU count + best-effort model name. None on platforms where neither works."""
    cpu_count = os.cpu_count()
    if cpu_count is None:
        return None
    model: Optional[str] = None
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        try:
            for line in cpuinfo.read_text().splitlines():
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break
        except Exception:
            pass
    return CpuInfo(cpu_count=cpu_count, cpu_model=model)


def get_uptime_seconds() -> Optional[int]:
    """System uptime in seconds. /proc/uptime first; falls back to `uptime`
    parse. None on non-Linux without /proc/uptime."""
    uptime = Path("/proc/uptime")
    if uptime.is_file():
        try:
            first_field = uptime.read_text().split()[0]
            return int(float(first_field))
        except Exception:
            pass
    # macOS fallback: `sysctl -n kern.boottime` (used = now - boot). Skip
    # for now — macOS dev environments don't need a uptime number.
    return None


# ── Top-level snapshot ────────────────────────────────────────────────


def get_all() -> ServerSnapshot:
    """One-call collection of everything. Each field is independently
    Optional so the response always serializes."""
    return ServerSnapshot(
        cpu=get_cpu_info(),
        memory=get_memory(),
        swap=get_swap(),
        disk_root=get_disk("/"),
        load=get_load(),
        uptime_seconds=get_uptime_seconds(),
    )


def to_dict(snap: ServerSnapshot) -> dict:
    """Serialize for the API response. Nested Optional dataclasses become
    nested dicts or None."""
    out: dict = {}
    for field, value in asdict(snap).items():
        out[field] = value  # asdict handles nested dataclasses recursively
    return out
