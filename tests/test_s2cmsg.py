import unittest
from backend import s2cmsg


class CatalogTests(unittest.TestCase):
    def test_catalog_ids_are_stable_snapshot(self) -> None:
        # KALICILIK KURALI: atanan ID asla degismez. Bu tablo bilerek
        # elle yazilmistir; katalogda ID degisirse bu test KIRILMALIDIR.
        expected = {
            "PING": 0x53430101, "VERSION": 0x53430102, "TRACE_LEVEL_SET": 0x53430103,
            "TRACE_EVENT": 0x53430181, "BUS_TRACE_EVENT": 0x53430182,
            "REGISTER_READ": 0x53430201, "REGISTER_WRITE": 0x53430202,
            "REGISTERS_READ": 0x53430203, "MEM_READ": 0x53430204,
            "MEM_WRITE": 0x53430205, "I2C_SCAN": 0x53430206, "I2C_MUX_SET": 0x53430207,
            "CIT_RUN": 0x53430301, "CIT_READ": 0x53430302,
            "DEVICE_INIT": 0x53430401, "VOLTAGE_READ": 0x53430402,
            "TEMPERATURE_READ": 0x53430403, "CURRENT_READ": 0x53430404,
            "VCC_READ": 0x53430405, "STATUS_READ": 0x53430406,
            "CONFIG_READ": 0x53430407, "ELAPSED_READ": 0x53430408,
            "ALARM_READ": 0x53430409, "EVENT_READ": 0x5343040A,
            "SENSE_READ": 0x5343040B, "ADIN_READ": 0x5343040C,
            "VOUT_READ": 0x5343040D, "POWER_READ": 0x5343040E,
            "HUMIDITY_READ": 0x5343040F, "USER_REGISTER_READ": 0x53430410,
            "ID_READ": 0x53430411, "DATA_READ": 0x53430412,
            "BYTE_WRITE": 0x53430413, "PAGE_WRITE": 0x53430414,
            "PAGE_PROGRAM": 0x53430415, "SECTOR_ERASE": 0x53430416,
            "PLL1_LOCK_DETECT": 0x53430417, "PLL1_LOCK_LOSS": 0x53430418,
            "PLL2_LOCK_DETECT": 0x53430419, "PLL2_LOCK_LOSS": 0x5343041A,
            "MULTIPLIER_LOCK_DETECT": 0x5343041B,
        }
        catalog = s2cmsg.load_catalog()
        actual = {m["name"]: int(m["id"], 16) for m in catalog["messages"]}
        for name, mid in expected.items():
            self.assertEqual(actual.get(name), mid, f"{name} ID degisti/yok!")
        # Tum ID'ler 0x5343 imzasini tasimali (resync varsayimi).
        for name, mid in actual.items():
            self.assertEqual(mid >> 16, 0x5343, name)

    def test_every_id_is_unique(self) -> None:
        catalog = s2cmsg.load_catalog()
        ids = [m["id"] for m in catalog["messages"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_real_wire_ops_resolve(self) -> None:
        # Kod tabaninin fiilen gonderdigi tel op'lari katalogda COZULMELI
        # (canli KeyError regresyon korumasi; kaynaklar: i2c_scan.py,
        # registers.py, register-map/BoardConnectionCard UI).
        for op in ("spec2code_version", "log_level", "i2c_mux_set", "i2c_scan",
                   "register_read", "register_write", "mem_read", "mem_write"):
            self.assertEqual(s2cmsg.message_id_for_op(op) >> 16, 0x5343, op)


class PackUnpackTests(unittest.TestCase):
    def test_request_roundtrip_header_and_alignment(self) -> None:
        frame = s2cmsg.pack_request("voltage_read", 7, device_index=2,
                                    register_address=0x0A, value=0x55, data=b"\x01\x02\x03")
        # 12B baslik + 28B sabit alanlar + 3B veri pad->4B = 44B govde
        self.assertEqual(len(frame), 12 + 28 + 4)
        parser = s2cmsg.FrameParser()
        frames = parser.feed(frame)
        self.assertEqual(len(frames), 1)
        cmd, counter, body = frames[0]
        self.assertEqual(cmd, 0x53430402)
        self.assertEqual(counter, 7)
        self.assertEqual(len(body) % 4, 0)

    def test_parser_resyncs_after_garbage(self) -> None:
        good = s2cmsg.pack_request("ping", 1)
        noisy = b"\xde\xad\xbe\xef\r\nboot log\n" + good + b"\x00" + good
        parser = s2cmsg.FrameParser()
        frames = parser.feed(noisy)
        self.assertEqual(len(frames), 2)
        self.assertTrue(all(f[0] == 0x53430101 for f in frames))

    def test_parser_survives_split_delivery(self) -> None:
        good = s2cmsg.pack_request("mem_read", 3, address=0xA0000000, length=4)
        parser = s2cmsg.FrameParser()
        out = []
        for i in range(len(good)):
            out += parser.feed(good[i:i + 1])
        self.assertEqual(len(out), 1)

    def test_unpack_response_maps_status_and_text(self) -> None:
        # Elle kurulmus yanit govdesi: sayac=7, durum=5 (BUS_HATASI),
        # iCihazDurum=-2, deger=0xCAFE, veri=2B, metin="I2C NACK"
        import struct
        body = struct.pack("<IIiII", 7, 5, -2, 0xCAFE, 2) + b"\xAB\xCD\x00\x00"
        text = b"I2C NACK"
        body += struct.pack("<I", len(text)) + text  # 8B, zaten 4 kati
        header = struct.pack("<III", 0x53430402 | s2cmsg.RESPONSE_BIT, len(body), 42)
        frames = s2cmsg.FrameParser().feed(header + body)
        parsed = s2cmsg.unpack_response(frames[0])
        self.assertEqual(parsed["id"], "7")
        self.assertEqual(parsed["ok"], "0")
        self.assertEqual(parsed["durum"], 5)
        self.assertEqual(parsed["status"], "-2")
        self.assertEqual(parsed["value"], "0xCAFE")
        self.assertEqual(parsed["data"], "ABCD")
        self.assertEqual(parsed["message"], "I2C NACK")


class ConsoleFrameSplitterTests(unittest.TestCase):
    def test_signature_split_across_two_feeds_recovers_frame(self) -> None:
        frame = s2cmsg.pack_request("ping", 1)
        splitter = s2cmsg.ConsoleFrameSplitter()
        console1, frames1 = splitter.feed(frame[:3])
        console2, frames2 = splitter.feed(frame[3:])
        self.assertEqual(frames1, [])
        self.assertEqual(len(frames2), 1)
        self.assertEqual(frames2[0][0], 0x53430101)
        self.assertEqual(frames2[0][1], 1)
        # Imza baytlarindan hicbiri console'a sizmamali.
        self.assertEqual(console1 + console2, b"")

    def test_body_split_across_feeds_recovers_frame(self) -> None:
        frame = s2cmsg.pack_request("mem_read", 3, address=0xA0000000, length=4)
        split_at = s2cmsg.HEADER_SIZE + 4  # baslik + govdenin bir kismi
        splitter = s2cmsg.ConsoleFrameSplitter()
        console1, frames1 = splitter.feed(frame[:split_at])
        console2, frames2 = splitter.feed(frame[split_at:])
        self.assertEqual(frames1, [])
        self.assertEqual(console1, b"")
        self.assertEqual(console2, b"")
        self.assertEqual(len(frames2), 1)
        command_id, counter, body = frames2[0]
        self.assertEqual(command_id, s2cmsg.message_id_for_op("mem_read"))
        self.assertEqual(counter, 3)
        self.assertEqual(len(body) % 4, 0)

    def test_console_text_around_frame_in_single_feed(self) -> None:
        frame = s2cmsg.pack_request("ping", 5)
        payload = b"boot log\r\n" + frame + b"devam"
        splitter = s2cmsg.ConsoleFrameSplitter()
        console, frames = splitter.feed(payload)
        leftover = splitter.flush()
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0][1], 5)
        # "devam" (5B) <= 3 bayt bekletme toleransindan buyuk oldugu icin en
        # azindan bir kismi hemen console'a dusmeli olabilir; flush ile
        # kalan kuyruk dahil edilince iki metin de tam olarak gorunmeli.
        combined = (console + leftover).decode("ascii", errors="replace")
        self.assertIn("boot log", combined)
        self.assertIn("devam", combined)

    def test_plain_text_feeds_produce_no_frames_and_preserve_bytes(self) -> None:
        splitter = s2cmsg.ConsoleFrameSplitter()
        chunks = [b"hello ", b"world\r\n", b"another line\r\n", b"tail"]
        console_total = b""
        frame_total: list[tuple[int, int, bytes]] = []
        for chunk in chunks:
            console, frames = splitter.feed(chunk)
            console_total += console
            frame_total += frames
        leftover = splitter.flush()
        self.assertEqual(frame_total, [])
        self.assertEqual(console_total + leftover, b"".join(chunks))

    def test_fake_signature_with_oversized_body_falls_back_to_console(self) -> None:
        # "CS" (0x43 0x53) gorunur ama boy alani 4096'yi asiyor -> sahte imza.
        text = b"prefix CS\xff\xff\xff\xffgarbage tail here"
        splitter = s2cmsg.ConsoleFrameSplitter()
        console, frames = splitter.feed(text)
        leftover = splitter.flush()
        self.assertEqual(frames, [])
        self.assertEqual(console + leftover, text)

    def test_frame_fed_one_byte_at_a_time_yields_single_frame(self) -> None:
        frame = s2cmsg.pack_request("ping", 9)
        splitter = s2cmsg.ConsoleFrameSplitter()
        frames: list[tuple[int, int, bytes]] = []
        console_total = b""
        for i in range(len(frame)):
            console, new_frames = splitter.feed(frame[i:i + 1])
            console_total += console
            frames += new_frames
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0][0], 0x53430101)
        self.assertEqual(frames[0][1], 9)
        self.assertEqual(console_total, b"")


if __name__ == "__main__":
    unittest.main()
