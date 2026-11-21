"""A modern calculator for Android (and desktop), built with Kivy.

Features:
- Safe expression evaluation (no eval())
- Backspace, percent, +/-, square, square root, parentheses
- Two-line display (expression + result)
- History popup (tap an entry to reuse its result)
- Keyboard support when run on a desktop (digits, + - * / . ( ) % Enter, Backspace)

Run on desktop to test:   python main.py
Build for Android:        see buildozer.spec
"""

import ast
import math
import operator
import re

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex as hex_color

# ---------- Theme ----------
BG = "#1e1e2e"
DISPLAY_BG = "#181825"
TEXT = "#cdd6f4"
SUBTEXT = "#8b90a8"
NUMBER_BG = "#313244"
OPERATOR_BG = "#fab387"
FUNCTION_BG = "#45475a"
EQUALS_BG = "#a6e3a1"
CLEAR_BG = "#f38ba8"
DARK_TEXT = "#11111b"

Window.clearcolor = hex_color(BG)

# ---------- Safe evaluation ----------
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](_eval_node(node.operand))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "sqrt"
        and len(node.args) == 1
    ):
        return math.sqrt(_eval_node(node.args[0]))
    raise ValueError("Unsupported expression")


def calculate(expression):
    """Evaluate a math expression string and return a formatted result."""
    cleaned = expression.replace("×", "*").replace("÷", "/").replace("√", "sqrt")
    cleaned = re.sub(r"(\d+\.?\d*)%", r"(\1/100)", cleaned)  # 50% -> (50/100)
    result = _eval_node(ast.parse(cleaned, mode="eval"))
    return format_number(result)


def format_number(value):
    """Show whole numbers without '.0' and trim floating point noise."""
    if isinstance(value, float):
        value = round(value, 10)
        if value.is_integer():
            value = int(value)
    return str(value)


# ---------- Button layout: (label, kind) ----------
# "DEL" is used instead of a symbol because some Android fonts lack the glyph.
BUTTON_ROWS = [
    [("C", "clear"), ("DEL", "func"), ("%", "func"), ("÷", "op")],
    [("x²", "func"), ("√", "func"), ("(", "func"), (")", "func")],
    [("7", "num"), ("8", "num"), ("9", "num"), ("×", "op")],
    [("4", "num"), ("5", "num"), ("6", "num"), ("-", "op")],
    [("1", "num"), ("2", "num"), ("3", "num"), ("+", "op")],
    [("±", "func"), ("0", "num"), (".", "num"), ("=", "equals")],
]

KIND_COLORS = {
    "num": (NUMBER_BG, TEXT),
    "op": (OPERATOR_BG, DARK_TEXT),
    "func": (FUNCTION_BG, TEXT),
    "clear": (CLEAR_BG, DARK_TEXT),
    "equals": (EQUALS_BG, DARK_TEXT),
}


class Display(BoxLayout):
    """Dark rounded-look panel with an expression line and a result line."""

    def __init__(self, on_history, **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(4), **kwargs)

        with self.canvas.before:
            Color(*hex_color(DISPLAY_BG))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        top = BoxLayout(size_hint_y=None, height=dp(36))
        history_btn = Button(
            text="History",
            size_hint_x=None,
            width=dp(90),
            background_normal="",
            background_color=hex_color(FUNCTION_BG),
            color=hex_color(TEXT),
            font_size=sp(14),
            on_release=lambda *_: on_history(),
        )
        top.add_widget(history_btn)
        top.add_widget(Label())  # spacer
        self.add_widget(top)

        self.expr_label = self._make_label(SUBTEXT, sp(18), size_hint_y=0.35)
        self.result_label = self._make_label(TEXT, sp(44), size_hint_y=0.65, bold=True)
        self.result_label.text = "0"

    def _make_label(self, color, size, bold=False, **kwargs):
        label = Label(
            text="",
            color=hex_color(color),
            font_size=size,
            bold=bold,
            halign="right",
            valign="middle",
            **kwargs,
        )
        label.bind(size=lambda lbl, s: setattr(lbl, "text_size", s))
        self.add_widget(label)
        return label

    def _update_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_expression(self, text):
        self.expr_label.text = text

    def set_result(self, text, font_size=None):
        self.result_label.text = text
        # Shrink long numbers so they stay on screen.
        if font_size is None:
            font_size = sp(44) if len(text) <= 10 else sp(30) if len(text) <= 16 else sp(22)
        self.result_label.font_size = font_size


class CalculatorApp(App):
    title = "Calculator"

    def build(self):
        self.expr = ""
        self.just_evaluated = False
        self.history = []  # list of (expression, result)

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        self.display = Display(on_history=self.open_history, size_hint_y=0.28)
        root.add_widget(self.display)
        root.add_widget(self.build_buttons())

        Window.bind(on_key_down=self.on_key_down)  # desktop keyboard support
        return root

    # ----- UI construction -----
    def build_buttons(self):
        grid = GridLayout(cols=4, spacing=dp(8), size_hint_y=0.72)
        for row in BUTTON_ROWS:
            for label, kind in row:
                bg, fg = KIND_COLORS[kind]
                grid.add_widget(
                    Button(
                        text=label,
                        font_size=sp(24),
                        bold=True,
                        background_normal="",
                        background_color=hex_color(bg),
                        color=hex_color(fg),
                        on_release=lambda _btn, value=label: self.on_button(value),
                    )
                )
        return grid

    # ----- Input handling -----
    def on_key_down(self, _window, key, _scancode, codepoint, _modifiers):
        if key == 13:  # Enter
            self.on_button("=")
        elif key == 8:  # Backspace
            self.on_button("DEL")
        elif codepoint:
            char = {"*": "×", "/": "÷"}.get(codepoint, codepoint)
            if char in "0123456789.+-×÷()%":
                self.on_button(char)

    def on_button(self, value):
        if value == "C":
            self.expr = ""
            self.just_evaluated = False
        elif value == "DEL":
            self.expr = self.expr[:-1]
        elif value == "=":
            self.evaluate()
            return
        elif value == "±":
            self.negate_last_number()
        elif value == "x²":
            if self.expr:
                self.append("**2")
        elif value == "√":
            self.append("√(", starts_new=True)
        else:
            self.append(value, starts_new=value.isdigit() or value in ".(")
        self.refresh()

    def append(self, text, starts_new=False):
        """Add text to the expression; a digit after '=' starts a fresh calculation."""
        if self.just_evaluated and starts_new:
            self.expr = ""
        self.just_evaluated = False
        self.expr += text

    def negate_last_number(self):
        match = re.search(r"\(-(\d+\.?\d*)\)$|\d+\.?\d*$", self.expr)
        if not match:
            return
        token = match.group(0)
        replacement = match.group(1) if token.startswith("(-") else f"(-{token})"
        self.expr = self.expr[: match.start()] + replacement

    def evaluate(self):
        if not self.expr:
            return
        try:
            result = calculate(self.expr)
        except ZeroDivisionError:
            self.show_error("Cannot divide by zero")
            return
        except Exception:
            self.show_error("Error")
            return
        self.history.insert(0, (self.expr, result))
        self.display.set_expression(self.expr + " =")
        self.display.set_result(result)
        self.expr = result
        self.just_evaluated = True

    def show_error(self, message):
        self.display.set_expression(self.expr)
        self.display.set_result(message, font_size=sp(22))
        self.expr = ""
        self.just_evaluated = False

    # ----- Display / history -----
    def refresh(self):
        self.display.set_expression(self.expr)
        self.display.set_result(self.expr or "0")

    def open_history(self):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))

        entries = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        entries.bind(minimum_height=entries.setter("height"))

        popup = Popup(
            title="History",
            content=content,
            size_hint=(0.92, 0.8),
            background_color=hex_color(BG),
        )

        if not self.history:
            entries.add_widget(
                Label(text="No calculations yet", size_hint_y=None, height=dp(48),
                      color=hex_color(SUBTEXT))
            )
        for expression, result in self.history:
            entries.add_widget(
                Button(
                    text=f"{expression} = {result}",
                    size_hint_y=None,
                    height=dp(52),
                    background_normal="",
                    background_color=hex_color(DISPLAY_BG),
                    color=hex_color(TEXT),
                    on_release=lambda _b, r=result: self.reuse_history(r, popup),
                )
            )

        scroll = ScrollView()
        scroll.add_widget(entries)
        content.add_widget(scroll)
        content.add_widget(
            Button(
                text="Clear history",
                size_hint_y=None,
                height=dp(48),
                background_normal="",
                background_color=hex_color(CLEAR_BG),
                color=hex_color(DARK_TEXT),
                on_release=lambda _b: self.clear_history(popup),
            )
        )
        popup.open()

    def reuse_history(self, result, popup):
        self.expr = result
        self.just_evaluated = True
        self.refresh()
        popup.dismiss()

    def clear_history(self, popup):
        self.history.clear()
        popup.dismiss()


if __name__ == "__main__":
    CalculatorApp().run()
