"""Execution engine for executable artifacts."""

from __future__ import annotations

import builtins
import json
import signal
import time
from contextlib import contextmanager
from types import FrameType, ModuleType
from typing import Any, Generator


def parse_json_args(args: list[Any]) -> list[Any]:
    parsed: list[Any] = []
    for arg in args:
        if isinstance(arg, str):
            trimmed = arg.strip()
            if (trimmed.startswith("{") and trimmed.endswith("}")) or (
                trimmed.startswith("[") and trimmed.endswith("]")
            ):
                try:
                    parsed.append(json.loads(trimmed))
                    continue
                except json.JSONDecodeError:
                    pass
        parsed.append(arg)
    return parsed


def _timeout_handler(_signum: int, _frame: FrameType | None) -> None:
    raise TimeoutError("execution timed out")


@contextmanager
def _timeout_context(seconds: int) -> Generator[None, None, None]:
    old_handler: Any = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(seconds)
    except (ValueError, AttributeError):
        # signal.alarm missing on some platforms, skip timeout enforcement
        pass
    try:
        yield
    finally:
        try:
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)
        except (ValueError, AttributeError):
            pass


class SafeExecutor:
    """Runs artifact code with kernel interfaces injected."""

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self.preloaded_modules: dict[str, Any] = {
            "json": json,
            "time": time,
        }

    def validate_code(self, code: str) -> tuple[bool, str]:
        if not code.strip():
            return False, "empty code"
        if "def run(" not in code and "def handle_request(" not in code and "def check_permission(" not in code:
            return False, "code must define run(), handle_request(), or check_permission()"
        try:
            compile(code, "<artifact>", "exec")
        except SyntaxError as exc:
            return False, f"syntax error: {exc}"
        except Exception as exc:  # pragma: no cover
            return False, f"compile error: {exc}"
        return True, ""

    def execute_with_invoke(
        self,
        *,
        code: str,
        args: list[Any] | None = None,
        caller_id: str | None = None,
        artifact_id: str | None = None,
        world: Any | None,
        current_depth: int = 0,
        max_depth: int = 5,
        entry_point: str = "run",
        method_name: str | None = None,
    ) -> dict[str, Any]:
        args = parse_json_args(args or [])
        valid, message = self.validate_code(code)
        if not valid:
            return {"success": False, "error": message}

        compiled = compile(code, "<artifact>", "exec")

        safe_builtins = dict(vars(builtins))
        globals_dict: dict[str, Any] = {
            "__builtins__": safe_builtins,
            "__name__": "__main__",
        }
        for module_name, module in self.preloaded_modules.items():
            globals_dict[module_name] = module

        payments: list[dict[str, Any]] = []

        def pay(target: str, amount: int) -> dict[str, Any]:
            if world is None or artifact_id is None:
                return {"success": False, "error": "pay unavailable"}
            if amount <= 0:
                return {"success": False, "error": "amount must be positive"}
            if not world.ledger.transfer_scrip(artifact_id, target, amount):
                return {"success": False, "error": "insufficient funds"}
            result = {"success": True, "target": target, "amount": amount}
            payments.append(result)
            return result

        def get_balance() -> int:
            if world is None:
                return 0
            principal = artifact_id or caller_id or ""
            return world.ledger.get_scrip(principal)

        def invoke(target_id: str, *invoke_args: Any) -> dict[str, Any]:
            if world is None:
                return {"success": False, "error": "invoke unavailable"}
            if caller_id is None:
                return {"success": False, "error": "caller_id missing"}
            if current_depth >= max_depth:
                return {"success": False, "error": f"max invoke depth {max_depth} exceeded"}
            return world.invoke_from_executor(
                caller_id=caller_id,
                target_id=target_id,
                method="run",
                args=list(invoke_args),
                current_depth=current_depth + 1,
                max_depth=max_depth,
            )

        globals_dict["pay"] = pay
        globals_dict["get_balance"] = get_balance
        globals_dict["invoke"] = invoke

        if caller_id is not None:
            globals_dict["caller_id"] = caller_id

        if world is not None:
            if caller_id is not None and hasattr(world.kernel_state, "for_principal"):
                globals_dict["kernel_state"] = world.kernel_state.for_principal(caller_id)
            else:
                globals_dict["kernel_state"] = world.kernel_state
            if caller_id is not None and hasattr(world.kernel_actions, "for_principal"):
                globals_dict["kernel_actions"] = world.kernel_actions.for_principal(caller_id)
            else:
                globals_dict["kernel_actions"] = world.kernel_actions

        if world is not None and artifact_id is not None:
            artifact = world.artifacts.get(artifact_id)
            if artifact is not None and "can_call_llm" in artifact.capabilities:

                def _syscall_llm(model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
                    payer = caller_id or artifact_id
                    return world.call_llm_as_syscall(
                        payer_id=payer,
                        model=model,
                        messages=messages,
                        tools=tools,
                    )

                globals_dict["_syscall_llm"] = _syscall_llm

        class Action:
            def invoke_artifact(self, target_id: str, method: str = "run", args: list[Any] | None = None) -> dict[str, Any]:
                result = invoke(target_id, *((args or [])))
                return result

            def pay(self, target: str, amount: int) -> dict[str, Any]:
                return pay(target, amount)

            def get_balance(self) -> int:
                return get_balance()

            def read_artifact(self, target_id: str) -> dict[str, Any]:
                if world is None:
                    return {"success": False, "error": "read unavailable"}
                state = globals_dict.get("kernel_state")
                if state is None or not hasattr(state, "read_artifact"):
                    return {"success": False, "error": "kernel_state unavailable"}
                content = state.read_artifact(target_id, caller_id or "")
                if content is None:
                    return {"success": False, "error": "not found or no access"}
                return {"success": True, "content": content}

        actions_module = ModuleType("actions")
        actions_module.Action = Action  # type: ignore[attr-defined]
        globals_dict["Action"] = Action

        try:
            with _timeout_context(self.timeout_seconds):
                exec(compiled, globals_dict)
        except TimeoutError:
            return {"success": False, "error": "code definition timed out"}
        except Exception as exc:
            return {"success": False, "error": f"code definition failed: {exc}"}

        entry = globals_dict.get(entry_point)
        if not callable(entry):
            return {"success": False, "error": f"entry point '{entry_point}' not found"}

        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        try:
            with _timeout_context(self.timeout_seconds):
                if entry_point == "handle_request":
                    result = entry(caller_id, method_name or "run", args)
                else:
                    result = entry(*args)
        except TimeoutError:
            return {
                "success": False,
                "error": "execution timed out",
                "execution_time_ms": (time.perf_counter() - wall_start) * 1000,
                "resources_consumed": {"cpu_seconds": max(0.0, time.process_time() - cpu_start)},
            }
        except Exception as exc:
            return {
                "success": False,
                "error": f"runtime error: {type(exc).__name__}: {exc}",
                "execution_time_ms": (time.perf_counter() - wall_start) * 1000,
                "resources_consumed": {"cpu_seconds": max(0.0, time.process_time() - cpu_start)},
            }

        try:
            json.dumps(result)
        except Exception:
            result = str(result)

        return {
            "success": True,
            "result": result,
            "execution_time_ms": (time.perf_counter() - wall_start) * 1000,
            "resources_consumed": {"cpu_seconds": max(0.0, time.process_time() - cpu_start)},
            "payments": payments,
        }


_executor: SafeExecutor | None = None


def get_executor(timeout_seconds: int | None = None) -> SafeExecutor:
    global _executor
    if _executor is None:
        _executor = SafeExecutor(timeout_seconds or 5)
    elif timeout_seconds is not None and timeout_seconds != _executor.timeout_seconds:
        _executor = SafeExecutor(timeout_seconds)
    return _executor
