#!/usr/bin/env python3
"""Vertical motion in a multiline draft. Up/Down move the cursor between visual lines while the
draft spans more than one line, and fall through to history recall at the boundaries: Up on the
first line recalls, Down on the last line is a no-op, and the live draft survives both."""

import harness

MOCK = """
text done
end-turn
"""


def test_up_moves_lines_then_falls_through_to_history():
    term = harness.Terminal(MOCK, extra_env={"HAX_NO_SESSION": "0"})
    term.wait_for("❯")

    # Seed one history entry so a boundary fall-through is distinguishable.
    term.type("stored")
    term.send("Enter")
    term.wait_for("done")

    # A three-line draft, cursor at the end of row three. Up twice moves the
    # cursor to row one (clamped to each row's end), marking each landing.
    term.type("line-one\nline-two\nline-three")
    term.send("Up")
    term.type("!")
    term.send("Up")
    term.type("@")

    # Down on the last line is history-next with nothing newer: a no-op.
    # (Not asserted here; the submitted draft below pins the full result.)

    # Up from the first line recalls history, stashing the draft.
    term.send("Up")
    screen = term.screen()
    harness.expect("stored" in screen, "Up on the first line recalls history")
    harness.expect("line-three" not in screen, "recall replaces the draft display")

    # Down past the newest entry restores the draft with the edits.
    term.send("Down")
    screen = term.screen()
    harness.expect("line-three" in screen, "Down restores the stashed draft")
    harness.expect("line-one@" in screen, "the draft kept the row-1 edit")
    harness.expect("line-two!" in screen, "the draft kept the row-2 edit")

    # Submit and assert the exact draft the editor holds.
    term.send("Enter")
    term.expect_screen(
        """
        ▌ line-one@
        line-two!
        line-three
        """
    )
    term.send("C-d")
    harness.expect(term.wait_exit() == 0, "Ctrl-D exits after the scenario")


def test_single_line_up_still_recalls_history():
    term = harness.Terminal(MOCK, extra_env={"HAX_NO_SESSION": "0"})
    term.wait_for("❯")
    term.type("stored")
    term.send("Enter")
    term.wait_for("❯")

    # S1: single-line behavior is unchanged.
    term.send("Up")
    harness.expect("stored" in term.screen(), "Up at an empty prompt recalls history")
    term.send("Down")
    term.send("C-d")
    harness.expect(term.wait_exit() == 0, "Ctrl-D exits on the restored empty prompt")


harness.main(globals())
