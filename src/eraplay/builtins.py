from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from eraplay.ast import Command

if TYPE_CHECKING:
    from eraplay.runtime import MiniRuntime


class BuiltinHandlers:
    def __init__(self, runtime: MiniRuntime) -> None:
        self.runtime = runtime
        self.call_handlers: dict[str, Callable[[], None]] = {
            "SALEITEM_CHECK": self._set_default_sale_items,
            "PRINT_SHOPCHARALIST": self._print_shop_chara_list,
        }
        self.command_handlers: dict[str, Callable[[Command], None]] = {
            "PRINT_ITEM": self._print_owned_items,
            "PRINT_SHOPITEM": self._print_shop_item_list,
        }

    def execute_call(self, target: str) -> bool:
        handler = self.call_handlers.get(target.upper())
        if handler is None:
            return False
        handler()
        return True

    def execute_command(self, command: Command) -> bool:
        handler = self.command_handlers.get(command.name)
        if handler is None:
            return False
        handler(command)
        return True

    def _set_default_sale_items(self) -> None:
        runtime = self.runtime
        owned = {
            int(key.split(":", 1)[1])
            for key, value in runtime.state.variables.items()
            if key.startswith("ITEM:") and value
        }
        sale_ids = [
            *(index for index in range(24) if index != 22),
            24,
            25,
            29,
            34,
            37,
            38,
            39,
            42,
        ]
        for item_id in range(100):
            runtime.state.variables[f"ITEMSALES:{item_id}"] = 0
        for item_id in sale_ids:
            if item_id not in owned:
                runtime.state.variables[f"ITEMSALES:{item_id}"] = 1

    def _print_owned_items(self, command: Command | None = None) -> None:
        runtime = self.runtime
        item_names = runtime.project.data.name_tables.get("ITEMNAME", {})
        owned = [
            f"{item_names[item_id]}({count})"
            for item_id in sorted(item_names)
            if item_id < 100
            for count in [runtime._eval_value(f"ITEM:{item_id}")]
            if isinstance(count, int) and count > 0
        ]
        if owned:
            runtime.console.print_line(f"拥有的物品： {' '.join(owned)}")

    def _print_shop_item_list(self, command: Command | None = None) -> None:
        runtime = self.runtime
        item_names = runtime.project.data.name_tables.get("ITEMNAME", {})
        prices = runtime.project.data.item_prices
        entries = [
            (item_id, item_names[item_id], prices.get(item_id, 0))
            for item_id in sorted(item_names)
            if item_id < 100 and runtime._eval_value(f"ITEMSALES:{item_id}")
        ]
        for offset in range(0, len(entries), 3):
            row = entries[offset : offset + 3]
            parts = [f"[{item_id}] {name}(${price})" for item_id, name, price in row]
            runtime.console.print_line(" ".join(parts))

    def _print_shop_chara_list(self) -> None:
        runtime = self.runtime
        item_names = runtime.project.data.name_tables.get("ITEMNAME", {})
        prices = runtime.project.data.item_prices
        page = runtime._eval_int("TFLAG:100")
        start = page * 60 + 100
        end = min(start + 60, 200)
        entries = [
            (index, item_names[index], prices.get(index, 0))
            for index in range(start, end)
            if index in item_names
        ]
        for offset in range(0, len(entries), 3):
            row = entries[offset : offset + 3]
            parts = [f"[{index}] {name} ({price} P)" for index, name, price in row]
            runtime.console.print_line("    ".join(parts))
