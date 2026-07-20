import threading
import time
from queue import Queue

import pytest

import jaide.repl as repl_module
from jaide.exceptions import ReplException
from jaide.repl import REPL, CommandRequest, execute_command, parse_line, run_interactive


def test_parse_alias_and_typed_arguments():
    request = parse_line("set a beef")

    assert request is not None
    assert request.name == "set"
    assert request.args == ("A", 0xBEEF)


def test_parse_quoted_windows_path():
    request = parse_line(r'load "C:\Program Files\jaide.bin" 0100')

    assert request is not None
    assert request.args == (r"C:\Program Files\jaide.bin", 0x0100)


def test_parse_rejects_values_larger_than_16_bits():
    with pytest.raises(ReplException, match="16-bit"):
        parse_line("break 10000")


def test_mset_uses_the_memory_bus(emu):
    request = parse_line("mset 0100 beef")

    assert request is not None
    execute_command(emu, request)

    assert emu.bus.read16(0x0100) == 0xBEEF


def test_repl_waits_for_command_completion_before_reading_again(monkeypatch):
    requests: Queue[CommandRequest] = Queue()
    lines = iter(("step", "quit"))
    reads = 0

    def fake_input(_prompt: str) -> str:
        nonlocal reads
        reads += 1
        return next(lines)

    monkeypatch.setattr("builtins.input", fake_input)

    thread = threading.Thread(target=REPL(requests).run)
    thread.start()

    step = requests.get(timeout=1)
    time.sleep(0.02)
    assert reads == 1

    step.completed.set()
    quit_request = requests.get(timeout=1)
    quit_request.completed.set()
    thread.join(timeout=1)

    assert not thread.is_alive()


def test_runtime_pumps_graphics_and_executes_commands_on_main_thread(monkeypatch):
    main_thread = threading.get_ident()
    graphics_ready = threading.Event()
    graphics_closed = threading.Event()

    class FakeGraphics:
        def __init__(self):
            self.ticks = 0

        def tick(self):
            self.ticks += 1
            if self.ticks == 3:
                graphics_ready.set()

    class FakeEmulator:
        def __init__(self, graphics):
            self.devices = [graphics]
            self.reset_thread = None

        def reset(self):
            self.reset_thread = threading.get_ident()

    def fake_repl_run(self):
        assert graphics_ready.wait(timeout=1)

        reset = CommandRequest("reset")
        self.requests.put(reset)
        assert reset.completed.wait(timeout=1)

        quit_request = CommandRequest("quit")
        self.requests.put(quit_request)
        assert quit_request.completed.wait(timeout=1)

    monkeypatch.setattr(repl_module, "Graphics", FakeGraphics)
    monkeypatch.setattr(repl_module.REPL, "run", fake_repl_run)
    monkeypatch.setattr(repl_module.pygame, "quit", graphics_closed.set)

    graphics = FakeGraphics()
    emulator = FakeEmulator(graphics)
    run_interactive(emulator)

    assert graphics.ticks >= 3
    assert graphics_closed.is_set()
    assert emulator.reset_thread == main_thread
