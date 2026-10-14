"""Click-to-cursor in the readline draft. While a draft has text, hax turns on SGR
mouse reporting (1000+1006) — off on the idle prompt so native drag-select keeps
working: a left press inside the painted draft anchors the area with a
cursor-position report and moves the caret to the clicked cell; release and wheel
reports are consumed without touching the buffer."""

import harness

MOCK = """
text done
end-turn
"""


def sgr_press(term: harness.Terminal, row: int, col: int) -> None:
    """Inject a raw SGR press report, as a mouse-tracking terminal would emit it."""
    seq = f"\x1b[<0;{col};{row}M".encode()
    term._run("send-keys", "-H", *(f"{b:02x}" for b in seq))


def sgr_event(term: harness.Terminal, button: int, row: int, col: int) -> None:
    suffix = "m" if button == 999 else "M"
    code = button if button != 999 else 0
    seq = f"\x1b[<{code};{col};{row}{suffix}".encode()
    term._run("send-keys", "-H", *(f"{b:02x}" for b in seq))


def mouse_reporting(term: harness.Terminal) -> bool:
    """Whether the pane's terminal has mouse reporting switched on by an app."""
    out = term._run("display-message", "-p", "-t", "hax", "#{mouse_any_flag}")
    return out.strip() == "1"


def test_click_places_cursor_in_draft():
    term = harness.Terminal(MOCK, extra_env={"HAX_NO_SESSION": "0"})
    term.wait_for("❯")

    # Reporting stays off on the idle prompt so terminals and multiplexers keep
    # native drag-select; it turns on with the draft.
    harness.expect(not mouse_reporting(term), "an idle prompt does not capture the mouse")
    term.type("ac")  # caret after "c"; prompt cells: "❯" col 1, " " col 2, text from 3
    harness.expect(mouse_reporting(term), "a draft with text captures the mouse")
    screen = term.screen()
    prompt_row = next(i for i, line in enumerate(screen.splitlines()) if "❯" in line) + 1

    # Click on the "c" cell (column 4): the caret lands before it, so typing inserts.
    sgr_press(term, prompt_row, 4)
    term.type("X")
    screen = term.screen()
    harness.expect("aXc" in screen, "click placed the caret before the clicked cell")

    # Wheel and release reports are swallowed: no text, and the caret keeps its
    # clicked position, so Y joins after X.
    sgr_event(term, 64, prompt_row, 4)
    sgr_event(term, 999, prompt_row, 4)
    term.type("Y")
    screen = term.screen()
    harness.expect("aXYc" in screen, "release and wheel reports left no trace")

    # A click above the painted area (the banner) is ignored, not a teleport.
    sgr_press(term, 1, 4)
    term.type("Z")
    screen = term.screen()
    harness.expect("aXYZc" in screen, "a click outside the draft did not move the caret")

    term.send("Enter")
    term.wait_for("done")
    screen = term.screen()
    harness.expect("aXYZc" in screen, "the submitted draft survived every mouse report")

    # The next prompt starts empty, so reporting goes back off.
    term.wait_for("❯")
    harness.expect(not mouse_reporting(term), "the idle prompt after a submit releases the mouse")

    term.send("C-d")
    harness.expect(term.wait_exit() == 0, "Ctrl-D exits after the scenario")


harness.main(globals())
