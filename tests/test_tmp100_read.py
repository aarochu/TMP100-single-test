"""Tests for tmp100_read.py. No hardware needed - a fake smbus2 stands in."""
import contextlib
import io
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def encode(celsius):
    """Pack a temperature the way a TMP100 does: 12-bit, left-justified."""
    raw = int(round(celsius / 0.0625))
    if raw < 0:
        raw += 4096
    value = raw << 4
    return [(value >> 8) & 0xFF, value & 0xFF]


class FakeBus:
    def __init__(self, channel, present=(0x4F,), temp=21.5, fail_after=0,
                 interrupt_after=0):
        self.channel = channel
        self.present = set(present)
        self.temp = temp
        self.fail_after = fail_after
        self.interrupt_after = interrupt_after
        self.reads = 0
        self.config_writes = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True
        return False

    def write_byte_data(self, addr, reg, val):
        if addr not in self.present:
            raise OSError(121, "Remote I/O error")
        self.config_writes.append((addr, reg, val))

    def read_i2c_block_data(self, addr, reg, n):
        if addr not in self.present:
            raise OSError(121, "Remote I/O error")
        self.reads += 1
        if self.interrupt_after and self.reads > self.interrupt_after:
            raise KeyboardInterrupt           # stands in for the user pressing Ctrl-C
        if self.fail_after and self.reads > self.fail_after:
            raise OSError(121, "Remote I/O error")
        return encode(self.temp)


def load_module(**bus_kwargs):
    """Import tmp100_read with a fake smbus2 in place; return (module, buses)."""
    buses = []

    def factory(channel):
        bus = FakeBus(channel, **bus_kwargs)
        buses.append(bus)
        return bus

    fake = types.ModuleType("smbus2")
    fake.SMBus = factory
    sys.modules["smbus2"] = fake
    sys.modules.pop("tmp100_read", None)
    import tmp100_read
    return tmp100_read, buses


def run_cli(argv, **bus_kwargs):
    """Run main() with the given argv; return (stdout, buses, SystemExit or None)."""
    module, buses = load_module(**bus_kwargs)
    out, raised = io.StringIO(), None
    old = sys.argv
    sys.argv = ["tmp100_read.py"] + [str(a) for a in argv]
    try:
        with contextlib.redirect_stdout(out):
            module.main()
    except SystemExit as exc:
        raised = exc
    finally:
        sys.argv = old
    return out.getvalue(), buses, raised


class DecodeTests(unittest.TestCase):
    def test_known_temperatures_round_trip(self):
        module, _ = load_module()
        bus = FakeBus(1)
        for celsius in (25.0, 0.0, -0.0625, -0.25, -12.5, -55.0, 125.0, 127.9375):
            bus.temp = celsius
            self.assertAlmostEqual(module.read_temp_c(bus, 0x4F), celsius, places=6)

    def test_negative_uses_twos_complement(self):
        module, _ = load_module()
        bus = FakeBus(1, temp=-25.0)
        self.assertLess(module.read_temp_c(bus, 0x4F), 0)


class AcquisitionTests(unittest.TestCase):
    def test_continuous_reads_and_summary(self):
        out, buses, raised = run_cli([0.05, 0.26])
        self.assertIsNone(raised)
        self.assertGreaterEqual(buses[0].reads, 3)
        self.assertIn("temp (C)", out)
        self.assertIn("21.500", out)
        self.assertIn("reading(s) over", out)
        self.assertIn("mean", out)
        self.assertTrue(buses[0].closed, "bus must be closed on exit")

    def test_sets_12_bit_resolution_before_reading(self):
        _, buses, _ = run_cli([0.05, 0.11])
        self.assertEqual(buses[0].config_writes, [(0x4F, 0x01, 0b1100000)])

    def test_missing_sensor_exits_with_guidance(self):
        out, buses, raised = run_cli([0.05, 0.11], present=())
        self.assertIsInstance(raised, SystemExit)
        self.assertIn("No TMP100 answered", str(raised.code))
        self.assertIn("i2cdetect", str(raised.code))
        self.assertTrue(buses[0].closed)

    def test_read_failure_is_counted_not_fatal(self):
        out, buses, raised = run_cli([0.05, 0.3], fail_after=2)
        self.assertIsNone(raised, "a dropped sensor must not crash the run")
        self.assertIn("ERR", out)
        self.assertIn("failed", out)
        self.assertIn("2 reading(s)", out)

    def test_duration_zero_means_no_time_limit(self):
        """The README tells 0x48 users to run `... 1 0 0x48`; 0 must not exit at once."""
        out, buses, raised = run_cli([0.01, 0, "0x48"],
                                     present=(0x48,), interrupt_after=3)
        self.assertIsNone(raised)
        self.assertEqual(buses[0].reads, 4)        # 3 good reads, then the interrupt
        self.assertIn("3 reading(s)", out)
        self.assertIn("0x48", out)

    def test_custom_address_argument(self):
        out, buses, raised = run_cli([0.05, 0.11, "0x48"], present=(0x48,))
        self.assertIsNone(raised)
        self.assertEqual(buses[0].config_writes[0][0], 0x48)
        self.assertIn("0x48", out)


if __name__ == "__main__":
    unittest.main()
