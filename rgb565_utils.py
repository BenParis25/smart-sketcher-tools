"""Helpers for packing RGB pixels into RGB565 byte order."""


def rgb_to_rgb565_bytes(r: int, g: int, b: int) -> tuple[int, int]:
    """Pack one RGB pixel into little-endian RGB565 bytes."""
    low_byte = ((g & 0x07) << 5) | (b >> 3)
    high_byte = (r & 0xF8) | (g >> 5)
    return low_byte, high_byte