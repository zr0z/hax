"""Kitty key reports at the prompt. hax pushes the disambiguate flag, so a supporting
terminal sends Shift+Enter as CSI 13;2 u — which must insert a newline instead of
submitting — and Ctrl chords as CSI codepoint;mod u, which replay through the same
byte keymap as the legacy control byte. tmux ignores the mode and keeps sending
legacy bytes; the reports are injected here to pin what the editor does with them."""

import harness

MOCK = """
text done
end-turn
"""


def test_shift_enter_key_report_inserts_newline():
    term = harness.Terminal(MOCK, extra_env={"HAX_NO_SESSION": "0"})
    term.wait_for("❯")

    term.type("ab")
    # Shift+Enter as a supporting terminal reports it: CSI 13 ; 2 u. A newline lands
    # in the draft instead of submitting, so the second segment stays editable.
    term.inject(b"\x1b[13;2u")
    term.type("cd")
    term.send("Enter")
    term.wait_for("done")

    # The submitted draft carries both segments: one user turn, two lines.
    screen = term.screen()
    harness.expect("▌ ab" in screen, "the key report did not submit the first line")
    harness.expect("▌ cd" in screen, "the key report split the draft into two lines")

    term.send("C-d")
    harness.expect(term.wait_exit() == 0, "Ctrl-D exits after the scenario")


def test_ctrl_chord_key_report_replays_the_legacy_byte():
    term = harness.Terminal(MOCK, extra_env={"HAX_NO_SESSION": "0"})
    term.wait_for("❯")

    term.type("draft")
    # Ctrl-C as CSI 99 ; 5 u: the report resolves to ^C, clearing the draft exactly
    # as the control byte does.
    term.inject(b"\x1b[99;5u")
    term.type("x")
    screen = term.screen()
    harness.expect("draft" not in screen, "the Ctrl-C key report cleared the draft")
    harness.expect("❯ x" in screen, "typing after the report starts a fresh draft")

    # Ctrl-U empties the draft, then Ctrl-D quits.
    term.send("C-u")
    term.send("C-d")
    harness.expect(term.wait_exit() == 0, "Ctrl-D exits after the scenario")


harness.main(globals())
