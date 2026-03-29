"""Tests for TPN_ACTIVE signal file."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.hapax_daimonion.cognitive_loop import write_tpn_active


class TestTpnSignal(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._tmp_file = Path(self._tmpdir) / "tpn_active"

    def test_write_active(self):
        write_tpn_active(True, self._tmp_file)
        assert self._tmp_file.read_text().strip() == "1"

    def test_write_inactive(self):
        write_tpn_active(False, self._tmp_file)
        assert self._tmp_file.read_text().strip() == "0"

    def test_write_overwrites(self):
        write_tpn_active(True, self._tmp_file)
        write_tpn_active(False, self._tmp_file)
        assert self._tmp_file.read_text().strip() == "0"

    def test_write_creates_parent(self):
        nested = Path(self._tmpdir) / "sub" / "tpn_active"
        write_tpn_active(True, nested)
        assert nested.read_text().strip() == "1"

    def test_write_failure_does_not_raise(self):
        write_tpn_active(True, Path("/proc/nonexistent/tpn_active"))
