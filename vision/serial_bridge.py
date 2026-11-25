"""
Modul khusus komunikasi USB Serial antara laptop/PC dan ESP32 (115200 baud).
Mendukung auto-detect port, auto-reconnect, dan mode --mock-serial tanpa ESP32.
"""

from __future__ import annotations

import time
from typing import Optional


def auto_detect_esp32_port() -> Optional[str]:
    """Mencari port serial USB-UART yang paling mungkin terhubung ke ESP32."""
    from serial.tools import list_ports

    ports = list(list_ports.comports())
    if not ports:
        return None

    keywords = ("cp210", "ch340", "ftdi", "usbserial", "slab", "esp32", "ttyusb", "ttyacm")
    for p in ports:
        desc = f"{p.device} {p.description} {p.manufacturer or ''}".lower()
        if any(k in desc for k in keywords):
            return p.device

    return ports[0].device


class Esp32SerialBridge:
    """Komunikasi serial dua arah ke ESP32 dengan auto-reconnect."""

    def __init__(self, port: str = "AUTO", baudrate: int = 115200) -> None:
        self.configured_port = port
        self.baudrate = baudrate
        self.active_port: Optional[str] = None
        self._ser = None
        self._last_reconnect_attempt = 0.0

    def connect(self) -> bool:
        """Membuka koneksi serial ke ESP32. Mengembalikan True bila berhasil."""
        import serial

        target_port = (
            auto_detect_esp32_port()
            if self.configured_port.upper() == "AUTO"
            else self.configured_port
        )
        if not target_port:
            return False

        try:
            self._ser = serial.Serial(target_port, self.baudrate, timeout=0.05)
            self.active_port = target_port
            return True
        except Exception:
            self._ser = None
            self.active_port = None
            return False

    def ensure_connected(self, retry_interval_sec: float = 2.0) -> bool:
        """Menjaga koneksi serial tetap aktif dengan auto-reconnect berkala."""
        if self._ser is not None and self._ser.is_open:
            return True

        now = time.monotonic()
        if now - self._last_reconnect_attempt < retry_interval_sec:
            return False
        self._last_reconnect_attempt = now
        return self.connect()

    def read_lines(self) -> list[str]:
        """Membaca seluruh baris teks yang tersedia dari ESP32 tanpa blocking."""
        if self._ser is None or not self._ser.is_open:
            return []

        lines: list[str] = []
        try:
            while self._ser.in_waiting > 0:
                raw = self._ser.readline().decode("utf-8", errors="replace").strip()
                if raw:
                    lines.append(raw)
        except Exception:
            self.close()
        return lines

    def send_command(self, message: str) -> bool:
        """Mengirim satu baris perintah berakhiran newline ke ESP32."""
        if self._ser is None or not self._ser.is_open:
            return False
        try:
            payload = f"{message.strip()}\n".encode("ascii")
            self._ser.write(payload)
            self._ser.flush()
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        """Menutup port serial dengan aman."""
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
            self.active_port = None


class MockSerialBridge:
    """Pengganti komunikasi serial untuk mode --mock-serial tanpa perangkat ESP32."""

    def __init__(self) -> None:
        self.active_port = "MOCK_SERIAL"
        self._pending_lines: list[str] = ["STATE:q0"]

    def connect(self) -> bool:
        return True

    def ensure_connected(self, retry_interval_sec: float = 2.0) -> bool:
        return True

    def trigger_mock_q2(self) -> None:
        """Memicu simulasi seolah ESP32 mengirim STATE:q2."""
        self._pending_lines.append("STATE:q2")

    def read_lines(self) -> list[str]:
        lines = list(self._pending_lines)
        self._pending_lines.clear()
        return lines

    def send_command(self, message: str) -> bool:
        print(f"[MOCK-SERIAL -> ESP32] Akan dikirim: {message.strip()}")
        self._pending_lines.append("STATE:q0")
        return True

    def close(self) -> None:
        pass
