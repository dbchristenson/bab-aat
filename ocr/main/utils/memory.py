import functools
import gc
import logging
import sys
import time
import tracemalloc
from contextlib import contextmanager
from typing import Any, Callable, Dict, List

import psutil
from memory_profiler import profile
from pympler import classtracker, muppy, summary, tracker

# Configure logger for this module
logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Comprehensive memory monitoring class for tracking memory usage and leaks."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.tracker = tracker.SummaryTracker()
        self.start_memory = None
        self.start_time = None
        self.snapshots = []
        self.process = psutil.Process()

        # Class tracker for specific object monitoring
        self.class_tracker = classtracker.ClassTracker()

    def start_monitoring(self, context: str = ""):
        """Start comprehensive memory monitoring."""
        if tracemalloc.is_tracing():
            tracemalloc.stop()

        tracemalloc.start(25)  # Track up to 25 frames
        self.start_memory = self.get_current_memory()
        self.start_time = time.time()

        logger.info(
            f"[{self.name}] Memory monitoring started {context}: "
            f"{self.start_memory:.1f}MB"
        )

        # Take initial snapshot
        self._take_snapshot(f"start_{context}")

    def log_memory_delta(self, context: str = ""):
        """Log memory changes since start with detailed analysis."""
        current = self.get_current_memory()
        delta = current - (self.start_memory or 0)
        elapsed = time.time() - (self.start_time or time.time())

        logger.info(
            f"[{self.name}] Memory {context}: {current:.1f}MB "
            f"(Δ{delta:+.1f}MB) after {elapsed:.1f}s"
        )

        # Take snapshot for this checkpoint
        self._take_snapshot(context)

        # Get tracemalloc snapshot if available
        if tracemalloc.is_tracing():
            self._log_tracemalloc_stats(context)

    def _take_snapshot(self, context: str):
        """Take a memory snapshot for later analysis."""
        snapshot = {
            "context": context,
            "timestamp": time.time(),
            "memory_mb": self.get_current_memory(),
            "objects": len(gc.get_objects()),
        }

        if tracemalloc.is_tracing():
            snapshot["tracemalloc"] = tracemalloc.take_snapshot()

        self.snapshots.append(snapshot)

    def _log_tracemalloc_stats(self, context: str, top_n: int = 5):
        """Log detailed tracemalloc statistics."""
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")

            logger.info(
                f"[{self.name}] Top {top_n} memory allocations for {context}:"
            )
            for i, stat in enumerate(top_stats[:top_n], 1):
                logger.info(f"  {i}. {stat}")

            # Also log by filename for broader view
            filename_stats = snapshot.statistics("filename")
            logger.info(f"[{self.name}] Top files by memory usage:")
            for i, stat in enumerate(filename_stats[:3], 1):
                logger.info(f"  {i}. {stat}")

        except Exception as e:
            logger.error(f"Failed to get tracemalloc stats: {e}")

    def get_current_memory(self) -> float:
        """Get current process memory in MB."""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / 1024 / 1024
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            return 0.0

    def get_memory_details(self) -> Dict[str, float]:
        """Get detailed memory information."""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()

            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": memory_percent,
                "available_mb": psutil.virtual_memory().available
                / 1024
                / 1024,
                "total_mb": psutil.virtual_memory().total / 1024 / 1024,
            }
        except Exception as e:
            logger.error(f"Failed to get detailed memory info: {e}")
            return {}

    def analyze_objects(self, top_n: int = 10):
        """Analyze objects in memory using pympler."""
        try:
            all_objects = muppy.get_objects()
            sum1 = summary.summarize(all_objects)

            logger.info(f"[{self.name}] Object analysis (top {top_n}):")
            formatted_summary_lines = list(summary.format_(sum1))
            for line in formatted_summary_lines[:top_n]:
                logger.info(f"  {line}")

            # Track specific object types
            self._track_specific_objects(all_objects)

        except Exception as e:
            logger.error(f"Object analysis failed: {e}")

    def _track_specific_objects(self, objects: List):
        """Track specific object types that commonly cause memory leaks."""
        # Count specific types
        type_counts = {}
        memory_heavy_types = ["ndarray", "Tensor", "DataFrame", "dict", "list"]

        for obj in objects:
            obj_type = type(obj).__name__
            if obj_type in memory_heavy_types:
                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

        if type_counts:
            logger.info(f"[{self.name}] Memory-heavy object counts:")
            for obj_type, count in sorted(
                type_counts.items(), key=lambda x: x[1], reverse=True
            ):
                logger.info(f"  {obj_type}: {count}")

    def track_memory_diff(self):
        """Track memory differences using pympler tracker."""
        try:
            logger.info(f"[{self.name}] Memory diff analysis:")
            self.tracker.print_diff()
        except Exception as e:
            logger.error(f"Memory diff tracking failed: {e}")

    def force_cleanup(self, aggressive: bool = True):
        """Force garbage collection and cleanup."""
        logger.info(
            f"[{self.name}] Forcing memory cleanup (aggressive={aggressive})..."
        )

        initial_memory = self.get_current_memory()

        # Multiple GC passes
        total_collected = 0
        passes = 5 if aggressive else 3

        for i in range(passes):
            collected = gc.collect()
            total_collected += collected
            logger.info(f"  GC pass {i+1}: collected {collected} objects")

        # Force cleanup of specific object types
        if aggressive:
            self._aggressive_cleanup()

        # Try to return memory to OS (Linux/Mac)
        self._return_memory_to_os()

        final_memory = self.get_current_memory()
        freed = initial_memory - final_memory

        logger.info(
            f"[{self.name}] Cleanup complete: "
            f"{initial_memory:.1f}MB → {final_memory:.1f}MB "
            f"(freed {freed:.1f}MB, collected {total_collected} objects)"
        )

    def _aggressive_cleanup(self):
        """Perform aggressive cleanup operations."""
        try:
            # Clear various caches
            if hasattr(sys, "_clear_type_cache"):
                sys._clear_type_cache()

            # Clear import cache for modules that might be holding references
            import importlib

            if hasattr(importlib, "invalidate_caches"):
                importlib.invalidate_caches()

        except Exception as e:
            logger.debug(f"Aggressive cleanup failed: {e}")

    def _return_memory_to_os(self):
        """Try to return memory to the operating system."""
        try:
            # Linux/Mac: use malloc_trim
            import ctypes

            try:
                libc = ctypes.CDLL("libc.so.6")  # Linux
                result = libc.malloc_trim(0)
                logger.debug(f"malloc_trim result: {result}")
            except OSError:
                try:
                    libc = ctypes.CDLL("libc.dylib")  # macOS
                    # macOS doesn't have malloc_trim, but we can try zone_pressure_relief
                    pass
                except OSError:
                    pass
        except Exception as e:
            logger.debug(f"Failed to return memory to OS: {e}")

    def log_system_memory(self):
        """Log system-wide memory information."""
        try:
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()

            logger.info(f"[{self.name}] System memory:")
            logger.info(f"  Total: {vm.total / 1024**3:.1f}GB")
            logger.info(
                f"  Available: {vm.available / 1024**3:.1f}GB ({vm.percent}% used)"
            )
            logger.info(
                f"  Swap: {swap.total / 1024**3:.1f}GB ({swap.percent}% used)"
            )

        except Exception as e:
            logger.error(f"Failed to get system memory info: {e}")

    def compare_snapshots(self, context1: str, context2: str):
        """Compare two memory snapshots."""
        snap1 = next(
            (s for s in self.snapshots if s["context"] == context1), None
        )
        snap2 = next(
            (s for s in self.snapshots if s["context"] == context2), None
        )

        if not snap1 or not snap2:
            logger.warning(
                f"Could not find snapshots for comparison: {context1}, {context2}"
            )
            return

        memory_diff = snap2["memory_mb"] - snap1["memory_mb"]
        object_diff = snap2["objects"] - snap1["objects"]
        time_diff = snap2["timestamp"] - snap1["timestamp"]

        logger.info(
            f"[{self.name}] Snapshot comparison ({context1} → {context2}):"
        )
        logger.info(f"  Memory: {memory_diff:+.1f}MB over {time_diff:.1f}s")
        logger.info(f"  Objects: {object_diff:+} objects")

        # Compare tracemalloc if available
        if "tracemalloc" in snap1 and "tracemalloc" in snap2:
            self._compare_tracemalloc_snapshots(
                snap1["tracemalloc"], snap2["tracemalloc"]
            )

    def _compare_tracemalloc_snapshots(self, snap1, snap2):
        """Compare two tracemalloc snapshots."""
        try:
            top_stats = snap2.compare_to(snap1, "lineno")
            logger.info("  Top memory allocation changes:")
            for i, stat in enumerate(top_stats[:3], 1):
                logger.info(f"    {i}. {stat}")
        except Exception as e:
            logger.debug(f"Failed to compare tracemalloc snapshots: {e}")

    def stop_monitoring(self, final_context: str = "stop"):
        """Stop monitoring and log final statistics."""
        self.log_memory_delta(final_context)
        self.log_system_memory()

        if tracemalloc.is_tracing():
            tracemalloc.stop()

        logger.info(f"[{self.name}] Memory monitoring stopped")

    def get_summary_report(self) -> str:
        """Generate a summary report of all monitoring data."""
        if not self.snapshots:
            return f"[{self.name}] No monitoring data available"

        initial = self.snapshots[0]
        final = self.snapshots[-1]
        peak_memory = max(s["memory_mb"] for s in self.snapshots)

        total_time = final["timestamp"] - initial["timestamp"]
        memory_change = final["memory_mb"] - initial["memory_mb"]

        report = [
            f"[{self.name}] Memory Monitoring Summary:",
            f"  Duration: {total_time:.1f} seconds",
            f"  Initial memory: {initial['memory_mb']:.1f}MB",
            f"  Final memory: {final['memory_mb']:.1f}MB",
            f"  Peak memory: {peak_memory:.1f}MB",
            f"  Net change: {memory_change:+.1f}MB",
            f"  Snapshots taken: {len(self.snapshots)}",
        ]

        return "\n".join(report)


# Decorator functions for easy monitoring
def memory_monitor(name: str = None, aggressive_cleanup: bool = False):
    """Decorator to monitor memory usage of functions."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            monitor_name = name or f"{func.__module__}.{func.__name__}"
            monitor = MemoryMonitor(monitor_name)

            monitor.start_monitoring(f"function {func.__name__}")

            try:
                result = func(*args, **kwargs)
                monitor.log_memory_delta("function completed")
                return result
            except Exception as e:
                monitor.log_memory_delta("function failed")
                raise
            finally:
                if aggressive_cleanup:
                    monitor.force_cleanup(aggressive=True)
                monitor.stop_monitoring()

                # Log summary
                logger.info(monitor.get_summary_report())

        return wrapper

    return decorator


def memory_profile_detailed(func: Callable) -> Callable:
    """Decorator for detailed line-by-line memory profiling."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Starting detailed memory profile for {func.__name__}")

        # Use memory_profiler's profile decorator
        profiled_func = profile(func)
        return profiled_func(*args, **kwargs)

    return wrapper


@contextmanager
def memory_context(
    name: str = "context",
    log_objects: bool = False,
    aggressive_cleanup: bool = False,
):
    """Context manager for monitoring memory usage in code blocks."""
    monitor = MemoryMonitor(name)
    monitor.start_monitoring("context start")

    try:
        if log_objects:
            monitor.analyze_objects()
        yield monitor
    except Exception as e:
        monitor.log_memory_delta("context failed")
        raise
    finally:
        monitor.log_memory_delta("context end")
        if log_objects:
            monitor.analyze_objects()
        if aggressive_cleanup:
            monitor.force_cleanup(aggressive=True)
        monitor.stop_monitoring()

        logger.info(monitor.get_summary_report())


def log_memory_usage(context: str = "", include_system: bool = False):
    """Simple function to log current memory usage."""
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        memory_percent = process.memory_percent()

        log_msg = f"Memory usage {context}: {memory_mb:.1f}MB ({memory_percent:.1f}%)"

        if include_system:
            vm = psutil.virtual_memory()
            log_msg += f" | System: {vm.percent}% used, {vm.available / 1024**3:.1f}GB available"

        logger.info(log_msg)

    except Exception as e:
        logger.error(f"Failed to log memory usage: {e}")


def check_memory_threshold(threshold_mb: float, context: str = "") -> bool:
    """Check if current memory usage exceeds threshold."""
    try:
        process = psutil.Process()
        current_mb = process.memory_info().rss / 1024 / 1024

        if current_mb > threshold_mb:
            logger.warning(
                f"Memory threshold exceeded {context}: "
                f"{current_mb:.1f}MB > {threshold_mb:.1f}MB"
            )
            return True
        return False

    except Exception as e:
        logger.error(f"Failed to check memory threshold: {e}")
        return False


def emergency_memory_cleanup():
    """Emergency memory cleanup function."""
    logger.warning("Emergency memory cleanup initiated!")

    monitor = MemoryMonitor("emergency")
    initial_memory = monitor.get_current_memory()

    # Aggressive cleanup
    monitor.force_cleanup(aggressive=True)

    final_memory = monitor.get_current_memory()
    freed = initial_memory - final_memory

    logger.warning(f"Emergency cleanup freed {freed:.1f}MB of memory")

    return freed
