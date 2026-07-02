#!/usr/bin/env python3
#
# Bake a line of text into a PNG and print its base64 — the exact form the
# gmlbroker forger embeds for its "Waiting for approval..." overlay
# (kWaitImgPngB64 in apps/gmlbroker/src/handshake_forger.cpp). The image is
# white text on a transparent canvas so it composites (Guacamole OVER, mode 14)
# onto whatever layer it is drawn over.
#
# Dependency-free: stdlib only (zlib + struct for the PNG, plus an embedded
# bitmap font). Glyphs are an 8x14 table baked once from Source Code Pro, so no
# font files or Pillow are needed at run time. Text is monospaced and blocky —
# fine for these overlays; size it with --scale (integer, crisp) or --font-size
# (any px height, nearest-neighbour scaled).
#
# Usage:
#   scripts/bake-text-image.py "Waiting for approval..."         # base64 to stdout
#   scripts/bake-text-image.py "Denied" -o denied.png            # also write the PNG
#   scripts/bake-text-image.py "Hello" --cpp --var kMyImgB64     # C++ literal to paste
#
# The --cpp form prints `constexpr int <var>W/H` dimensions plus the chunked
# `const char *<var>` string literal, ready to drop into the forger; the width
# and height are what the caller needs to centre the image on the display.

import argparse
import base64
import struct
import sys
import zlib

# 8x14 bitmap font for printable ASCII 32..126, baked from Source Code Pro.
# Each glyph is 14 bytes (one per row, MSB = leftmost pixel). Regenerate with the
# generator noted in the repo history if the cell size ever changes.
FONT_W, FONT_H = 8, 14
_FONT_B64 = (
    "AAAAAAAAAAAAAAAAAAAAAAAAEBAQEAAQEAAAAAAAAAhoaAgAAAAAAAAAAAAAKCh8KCh4AAAA"
    "AAAAAAAQOEBgOAxMMBAAAAAAAGCkqGAMFFQMAAAAAAAAMFBQIGRcSHQAAAAAAAAQEBAQAAAA"
    "AAAAAAAAAAgQECAgICAQEAgAAAAAACAQEBAQEBAgAAAAAAAAABAQODAIAAAAAAAAAAAAEBB8"
    "EBAAAAAAAAAAAAAAAAAAEBAQECAAAAAAAAAAfAAAAAAAAAAAAAAAAAAAABAQAAAAAAAACAgI"
    "EBAAICBAQAAAAAA4SERURERIOAAAAAAAADAQEBAQEBB8AAAAAAAAeEgICBgQIHwAAAAAAAB4"
    "CAgwCAQMeAAAAAAAAAgYKEhIfAgIAAAAAAAAeEBAeAwEDHgAAAAAAAA4YEBYTEREOAAAAAAA"
    "AHwICBAQEBAwAAAAAAAAOEhAOFhERDgAAAAAAAA4SERMNAQIcAAAAAAAAAAAEBAAABAQAAAA"
    "AAAAAAAQEAAAEBAQECAAAAAAABggYBAIAAAAAAAAAAAAAHwAfAAAAAAAAAAAAEAgGAgwQAAA"
    "AAAAAAAwCAgYEAAQMAAAAAAAAAA4REQcJBxAIBgAAAAAEDAoKEh8RIQAAAAAAAB4TEh4RERE"
    "eAAAAAAAADhgQEBAQGA4AAAAAAAAeExERERETHgAAAAAAAB8QEB4QEBAfAAAAAAAAHxAQHhA"
    "QEBAAAAAAAAAOEBAQExERDgAAAAAAABERER8RERERAAAAAAAAHgQEBAQEBB4AAAAAAAAOAgI"
    "CAgISDgAAAAAAABESFBwaEhERAAAAAAAAEBAQEBAQEB8AAAAAAAATExsbHRUREQAAAAAAABE"
    "ZGRUVFxMTAAAAAAAADhMREREREw4AAAAAAAAeERETHhAQEAAAAAAAAA4TERERERMOBAMAAAA"
    "AHhEREx4SEhEAAAAAAAAOEBAMBgERHgAAAAAAAB8EBAQEBAQEAAAAAAAAEREREREREw4AAAA"
    "AAAARERISCgoMBAAAAAAAACEhJR0dGxsbAAAAAAAAERoKDAwKEhEAAAAAAAAREQoKDAQEBAA"
    "AAAAAAB8CAgQMCBAfAAAAAAAADggICAgICAgIBgAAAAAQCAgIBAQEAgIAAAAAABwEBAQEBAQ"
    "EBBwAAAAAAAQMChIAAAAAAAAAAAAAAAAAAAAAAAAfAAAAAAgAAAAAAAAAAAAAAAAAAAAOAwc"
    "REx8AAAAAAAAQEB4RERETHgAAAAAAAAAADhAQEBAOAAAAAAAAAQEPExEREx8AAAAAAAAAAA4"
    "RHxAQDgAAAAAAAAcEHwQEBAQEAAAAAAAAAAAPEhIeEB8REQ4AAAAQEBYREREREQAAAAAAAAQ"
    "AHAQEBAQEAAAAAAAABAAcBAQEBAQEBBwAAAAQEBMSFBoSEQAAAAAAABwEBAQEBAQHAAAAAAA"
    "AAAAfFRUVFRUAAAAAAAAAABYREREREQAAAAAAAAAADhMRERMOAAAAAAAAAAAeEREREx4QEBA"
    "AAAAAAA8TERETDwEBAQAAAAAABwgICAgIAAAAAAAAAAAOEBwDAR4AAAAAAAAICB8ICAgIBwA"
    "AAAAAAAAAERERERMdAAAAAAAAAAARERIKDAQAAAAAAAAAACQlPRkbGwAAAAAAAAAAEgoMDAo"
    "TAAAAAAAAAAARERIKCgQECBgAAAAAAB8CBAgYHwAAAAAAAAYEBAQIBAQEBAIAAAAABAQEBAQ"
    "EBAQEBAQAAAAYBAQEBgQEBAQYAAAAAAAAAAgWAAAAAAAAA=="
)
_FONT = base64.b64decode(_FONT_B64)


def _chunk(tag, data):
    """Wrap a PNG chunk: length, type, data, CRC32(type+data)."""
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))


def encode_png(width, height, rgba):
    """Encode raw RGBA bytes (width*height*4) as an 8-bit RGBA PNG (stdlib only)."""
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)                         # filter type 0 (None) per scanline
        raw += rgba[y * stride:(y + 1) * stride]
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def render(text, cw, ch, color, bg, pad):
    """Rasterise `text` (monospaced) onto a `bg` canvas with `pad` border,
    painting set glyph pixels in `color`. Each glyph is drawn into a `cw`x`ch`
    cell by nearest-neighbour sampling the 8x14 source, so `cw`/`ch` may be any
    size (an integer multiple reproduces the crisp bitmap exactly). Returns
    (w, h, rgba bytes)."""
    w = pad * 2 + cw * len(text)
    h = pad * 2 + ch
    fg, bgb = bytes(color), bytes(bg)
    rgba = bytearray(bgb * (w * h))
    for i, character in enumerate(text):
        cp = ord(character)
        if not (32 <= cp < 127):              # outside the table -> blank cell
            continue
        base, gx0 = (cp - 32) * FONT_H, pad + i * cw
        for oy in range(ch):
            bits = _FONT[base + oy * FONT_H // ch]   # nearest source row
            for ox in range(cw):
                if (bits >> (7 - ox * FONT_W // cw)) & 1:   # nearest source col
                    off = ((pad + oy) * w + gx0 + ox) * 4
                    rgba[off:off + 4] = fg
    return w, h, bytes(rgba)


def as_cpp(b64, var, width, height):
    """Format the base64 as a pasteable C++ block: dimension constants plus a
    chunked string literal, matching the forger's existing kWaitImgPngB64."""
    chunks = "\n".join('    "%s"' % b64[i:i + 76] for i in range(0, len(b64), 76))
    return (f"constexpr int {var}W = {width};\n"
            f"constexpr int {var}H = {height};\n"
            f"const char *{var} =\n{chunks};")


def parse_rgba(spec, default):
    """Parse a colour: 'none'/'transparent' -> (0,0,0,0), or 'R,G,B[,A]'."""
    if spec is None:
        return default
    if spec.lower() in ("none", "transparent"):
        return (0, 0, 0, 0)
    parts = [int(x) for x in spec.split(",")]
    if len(parts) == 3:
        parts.append(255)
    if len(parts) != 4 or not all(0 <= v <= 255 for v in parts):
        raise ValueError(f"bad colour {spec!r}: use R,G,B[,A] with 0-255")
    return tuple(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Bake text into a PNG and print its base64 (forger overlay format).")
    ap.add_argument("text", help="the text to render")
    ap.add_argument("-o", "--out", metavar="FILE",
                    help="also write the PNG image to this file")
    size = ap.add_mutually_exclusive_group()
    size.add_argument("--scale", type=int,
                      help="integer pixel scale of the 8x14 font (default 3)")
    size.add_argument("--font-size", type=int, metavar="PX",
                      help="glyph height in px (any value; scales the bitmap)")
    ap.add_argument("--color", help="text colour R,G,B[,A] (default 255,255,255)")
    ap.add_argument("--bg", help="background R,G,B[,A] or 'none' (default none)")
    ap.add_argument("--pad", type=int, default=12, help="padding in px (default 12)")
    ap.add_argument("--cpp", action="store_true",
                    help="emit a pasteable C++ literal instead of raw base64")
    ap.add_argument("--var", default="kTextImgB64",
                    help="C++ variable name for --cpp (default kTextImgB64)")
    args = ap.parse_args(argv)

    if args.font_size is not None:
        if args.font_size < 1:
            ap.error("--font-size must be >= 1")
        ch = args.font_size
        cw = max(1, round(ch * FONT_W / FONT_H))
    else:
        scale = 3 if args.scale is None else args.scale
        if scale < 1:
            ap.error("--scale must be >= 1")
        cw, ch = FONT_W * scale, FONT_H * scale
    try:
        color = parse_rgba(args.color, (255, 255, 255, 255))
        bg = parse_rgba(args.bg, (0, 0, 0, 0))
    except ValueError as e:
        ap.error(str(e))

    w, h, rgba = render(args.text, cw, ch, color, bg, args.pad)
    png = encode_png(w, h, rgba)
    b64 = base64.b64encode(png).decode()

    if args.out:
        with open(args.out, "wb") as f:
            f.write(png)
        print(f"wrote {args.out} ({w}x{h}, {len(png)} bytes)", file=sys.stderr)

    if args.cpp:
        print(as_cpp(b64, args.var, w, h))
    else:
        print(b64)


if __name__ == "__main__":
    main()
