"""
ta2_decode.py
Decode TA2 (or AS2) files from the game into 8-bit indexed PNGs.

Usage:
    python ta2_decode.py INPUT.TA2 [INPUT2.TA2 ...] [-o OUTDIR]

For example, to decode every TA2 in an extracted disc's VISUAL folder
into PNG form:

    python ta2_decode.py extracted/VISUAL/*.TA2 -o decoded

Each input file is written to OUTDIR with its stem and a .png extension.
If the source TA2 has an embedded palette the PNG is saved as 8-bit
indexed. Otherwise it's saved as 8-bit greyscale.
"""

from __future__ import annotations
import argparse, sys, traceback
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ta2_codec


def save_png(decoded: dict, out_path: Path):
    w, h = decoded["w"], decoded["h"]
    if decoded["palette"]:
        img = Image.frombytes("P", (w, h), decoded["pixels"])
        pal: list[int] = []
        for r, g, b in decoded["palette"]:
            pal.extend([r, g, b])
        img.putpalette(pal)
        img.save(out_path, format="PNG")
    else:
        Image.frombytes("L", (w, h), decoded["pixels"]).save(out_path, format="PNG")


def main():
    ap = argparse.ArgumentParser(description="Decode TA2/AS2 files to PNG.")
    ap.add_argument("inputs", nargs="+", help="TA2/AS2 file(s) to decode")
    ap.add_argument("-o", "--out-dir", default=".",
                    help="output directory (default: current dir)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for inp in args.inputs:
        inp = Path(inp)
        print(f"\n{inp.name} ({inp.stat().st_size} bytes)")
        try:
            data = inp.read_bytes()
            decoded = ta2_codec.decode_ta2(data)
            out = out_dir / (inp.stem + ".png")
            save_png(decoded, out)
            pal_note = "indexed" if decoded["palette"] else "greyscale"
            print(f"  wrote {out}  ({decoded['w']}x{decoded['h']}, {pal_note})")
        except Exception as e:
            print(f"  decode failed: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
