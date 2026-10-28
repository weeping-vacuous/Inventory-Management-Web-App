import datetime
import functools
import threading
from collections import deque

class Logger:
    _lock = threading.Lock()
    # In-memory recent log buffer for high-performance dashboard access
    _recent_logs = deque(maxlen=300)
    LOG_FILE = 'Acitvity.log'

    @classmethod
    def log(cls, message, level="INFO"):
        """Writes a log entry to both disk file and in-memory buffer in a thread-safe manner."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": timestamp,
            "level": level,
            "message": str(message),
            "raw": f"[{timestamp}] [{level}] {message}"
        }

        with cls._lock:
            cls._recent_logs.append(entry)
            log_line = f"[{timestamp}] [{level}] {message}\n"
            try:
                with open(cls.LOG_FILE, 'a', encoding='utf-8') as log_file:
                    log_file.write(log_line)
            except Exception as e:
                print(f"Failed to write log entry to {cls.LOG_FILE}: {e}")

    @classmethod
    def log_activity(cls, func):
        """Decorator to automatically log function calls, arguments, successes, and errors."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # args[0] is usually 'self' for method calls
            passed_args = args[1:] if len(args) > 1 else ()
            cls.log(f"Calling function '{func.__name__}' with args: {passed_args} and kwargs: {kwargs}", level="INFO")

            try:
                result = func(*args, **kwargs)
                cls.log(f"Function '{func.__name__}' completed successfully", level="SUCCESS")
                return result
            except Exception as e:
                cls.log(f"Function '{func.__name__}' failed with error: {e}", level="ERROR")
                raise e
        return wrapper

    @classmethod
    def get_recent_logs(cls, limit=100, level_filter=None, query=None):
        """Returns the most recent logs, optionally filtered by level or search term."""
        with cls._lock:
            # If buffer is empty (e.g. on fresh server boot), prefill from disk file if available
            if not cls._recent_logs:
                cls._load_from_disk()
            
            logs = list(cls._recent_logs)

        # Apply filtering
        if level_filter and level_filter.upper() != "ALL":
            target = level_filter.upper()
            logs = [entry for entry in logs if entry.get("level") == target]

        if query:
            q = query.lower()
            logs = [entry for entry in logs if q in entry.get("message", "").lower() or q in entry.get("timestamp", "")]

        # Return latest entries up to limit (newest last or newest first according to limit)
        return logs[-limit:]

    @classmethod
    def _load_from_disk(cls):
        """Reads recent entries from disk into the in-memory cache upon server startup."""
        try:
            with open(cls.LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-200:]:
                    line = line.strip()
                    if not line:
                        continue
                    # Parse timestamp and message if format matches
                    level = "INFO"
                    if "failed with error" in line or "[ERROR]" in line:
                        level = "ERROR"
                    elif "completed successfully" in line or "[SUCCESS]" in line:
                        level = "SUCCESS"

                    cls._recent_logs.append({
                        "timestamp": line[1:20] if line.startswith("[") and len(line) > 20 else "",
                        "level": level,
                        "message": line,
                        "raw": line
                    })
        except FileNotFoundError:
            pass
