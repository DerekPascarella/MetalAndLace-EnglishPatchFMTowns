"""
ta2_encode.py
Convert a 640x480 PNG into a TA2 file the game can load.

Usage:
    python ta2_encode.py INPUT.png [INPUT2.png ...] [-o OUTDIR] [--no-verify]

The input PNG should be 8-bit indexed (mode 'P' in Pillow). Anything else
gets quantised to 256 colours on the way in, which usually works fine for
simple title-screen art but may not for photographic content.

Each input.png produces a TA2 file with the same stem next to it (or in
OUTDIR if -o is given). For example,

    python ta2_encode.py screen.png -o out

writes out/screen.TA2.

By default the script round-trips its output back through the decoder and
verifies that the pixels match the source PNG before declaring success.
Pass --no-verify to skip that step.

Once you have the TA2 file you still need to splice it back into the game's
disc image using a tool like cd-replace.
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ta2_codec


def png_to_indexed(path: Path):
    """Open a 640x480 PNG and return (pixel_bytes, 256-entry RGB palette)."""
    img = Image.open(path)
    if img.mode != "P":
        img = img.convert("RGB").quantize(colors=256)
    if img.size != (640, 480):
        raise ValueError(f"{path.name}: expected 640x480, got {img.size}")

    pal_raw = img.getpalette()
    if pal_raw is None:
        raise ValueError(f"{path.name}: no palette in indexed image")
    palette = [(pal_raw[i * 3], pal_raw[i * 3 + 1], pal_raw[i * 3 + 2])
               for i in range(256)]
    return img.tobytes(), palette


def main():
    ap = argparse.ArgumentParser(description="Encode PNG to TA2.")
    ap.add_argument("inputs", nargs="+", help="input PNG file(s)")
    ap.add_argument("-o", "--out-dir", default=".",
                    help="output directory (default: current dir)")
    ap.add_argument("--no-verify", dest="verify", action="store_false",
                    default=True,
                    help="skip the round-trip pixel-match check")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for inp in args.inputs:
        inp = Path(inp)
        print(f"\n{inp.name}")
        pixels, palette = png_to_indexed(inp)
        encoded = ta2_codec.encode_ta2(pixels, palette, 640, 480)
        out_path = out_dir / (inp.stem + ".TA2")
        out_path.write_bytes(encoded)
        print(f"  wrote {out_path}  ({len(encoded)} bytes)")

        if args.verify:
            rt = ta2_codec.decode_ta2(encoded)
            ok = rt["pixels"] == pixels
            print(f"  round-trip verify: {'ok' if ok else 'FAILED'}")
            if not ok:
                for i, (a, b) in enumerate(zip(pixels, rt["pixels"])):
                    if a != b:
                        print(f"    first mismatch at pixel {i} "
                              f"(x={i % 640}, y={i // 640}): "
                              f"src=0x{a:02x} decoded=0x{b:02x}")
                        break


if __name__ == "__main__":
    main()
