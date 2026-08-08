from typing import Protocol

import psutil


class MetricsAdapter(Protocol):
    def cpu_usage(self) -> float: ...

    def memory_usage(self) -> dict[str, float]: ...

    def top_processes(self, limit: int) -> list[dict[str, float | str]]: ...


class LocalMetricsAdapter:
    def cpu_usage(self) -> float:
        return float(psutil.cpu_percent(interval=0.1))

    def memory_usage(self) -> dict[str, float]:
        memory = psutil.virtual_memory()
        return {
            "percent": float(memory.percent),
            "used_gb": memory.used / (1024**3),
            "total_gb": memory.total / (1024**3),
        }

    def top_processes(self, limit: int) -> list[dict[str, float | str]]:
        rows: list[dict[str, float | str]] = []
        for process in psutil.process_iter(["name", "memory_info"]):
            try:
                info = process.info
                memory_info = info.get("memory_info")
                rows.append(
                    {
                        "name": str(info.get("name") or "unknown"),
                        "memory_mb": (memory_info.rss / (1024**2)) if memory_info else 0.0,
                    }
                )
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        return sorted(rows, key=lambda row: float(row["memory_mb"]), reverse=True)[:limit]
