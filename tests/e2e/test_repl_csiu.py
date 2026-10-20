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


def test_double_ctrl_c_key_report_quits():
    term = harness.Terminal(MOCK, extra_env={"HAX_NO_SESSION": "0"})
    term.wait_for("❯")

    # Ctrl-C twice on an empty prompt quits, whether it arrives as ^C or as a
    # key report: the escape transporting the report must not disarm the arming.
    term.inject(b"\x1b[99;5u")
    term.inject(b"\x1b[99;5u")
    harness.expect(term.wait_exit() == 0, "two Ctrl-C key reports quit on an empty prompt")


def test_escape_event_disarms_exit_arming():
    term = harness.Terminal(MOCK, extra_env={"HAX_NO_SESSION": "0"})
    term.wait_for("❯")

    # A Ctrl-C report arms, like ^C.
    term.inject(b"\x1b[99;5u")
    term.wait_for("ctrl+c again to exit")

    # An escape-transported event that does nothing (Page Up) must still disarm:
    # the lead byte alone may not carry the arming across, or two Ctrl-C reports
    # separated by any key would quit. Re-arming shows the hint again, and the
    # session has to be alive to paint it.
    term.inject(b"\x1b[5~")
    term.inject(b"\x1b[99;5u")
    term.type("x")
    term.wait_for("❯ x")

    # Disarmed again by the keystroke: clear, arm, quit — the legacy sequence.
    term.send("C-c")
    term.inject(b"\x1b[99;5u")
    term.wait_for("ctrl+c again to exit")
    term.inject(b"\x1b[99;5u")
    harness.expect(term.wait_exit() == 0, "the second Ctrl-C key report quits")


harness.main(globals())
