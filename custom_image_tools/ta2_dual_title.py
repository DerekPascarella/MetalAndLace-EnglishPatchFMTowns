"""
ta2_dual_title.py
Build a replacement title-screen TA2 pair while preserving the game's
dual-image fade effect.

The original title screen is encoded across two files:

    DM_TTL1.TA2   pixel data + colour palette for the illustration.
                  Contains 14 palette indices (0..13). Indices 0..6 form
                  the girl illustrations, indices 7..13 form the title
                  text "shape". DM_TTL1's palette intentionally duplicates
                  the illustration colours into the 7..13 slots, so the
                  text shape is invisible when this palette is active.
    DM_TTL2.TA2   palette only. Its pixel data is discarded at load time
                  (DM_TTL1's load overwrites the framebuffer). Its palette
                  recolours indices 0..6 as black and indices 7..13 as
                  white, which inverts which pixels are visible: now you
                  see the title text instead of the illustration.

The game cross-fades between the two palettes, producing a "scroll/fade
in" effect where the illustration dissolves into the title text without
the pixel data ever changing.

This script rebuilds the pair so that the title text becomes whatever
your replacement PNG's non-background pixels spell out.

Usage:
    python ta2_dual_title.py \\
        --original-ttl1 PATH/TO/DM_TTL1.TA2 \\
        --text-png      PATH/TO/your_text.png \\
        [--text-color   #RRGGBB] \\
        [-o OUTDIR]

PATH/TO/DM_TTL1.TA2 should be the unmodified original from the game
disc. It provides the illustration that survives into the new title.
your_text.png is a 640x480 PNG whose non-background pixels are treated
as a mask for the new text shape. The most common colour in the PNG is
assumed to be background.

--text-color is the colour the text appears in after the fade. The
default takes the most common non-background colour from the PNG, but
because phase-2 text can only be a single colour in this encoding, you
may want to pass --text-color #ffffff (matches the original game) or a
specific tone of your choice.

Output:
    OUTDIR/DM_TTL1.TA2          new title illustration + text mask
    OUTDIR/DM_TTL2.TA2          new palette-only fade target
    OUTDIR/_preview_phase1.png  what the screen looks like before the fade
    OUTDIR/_preview_phase2.png  what the screen looks like after the fade

Splice both files back into your disc image at the same paths
(\\VISUAL\\DM_TTL1.TA2 and \\VISUAL\\DM_TTL2.TA2).

Note: the phase-2 text is necessarily a single colour. The fade encoding
ties each text pixel's palette index to the woman shade underneath it, so
the same set of indices can't carry a gradient. If you want gradient text
you would need to redesign the pixel layout from scratch (much bigger
palette, multiple-image overlay, etc.).
"""

from __future__ import annotations
import argparse, sys
from pathlib import Path
from collections import Counter
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ta2_codec


def png_to_text_mask(png_path: Path):
    """Read PNG, return (bool mask per pixel, detected text colour)."""
    img = Image.open(png_path).convert("RGB")
    if img.size != (640, 480):
        raise ValueError(f"{png_path.name}: expected 640x480, got {img.size}")

    pixels = list(img.getdata())
    bg = Counter(pixels).most_common(1)[0][0]
    mask = [p != bg for p in pixels]

    non_bg = [p for p in pixels if p != bg]
    detected = Counter(non_bg).most_common(1)[0][0] if non_bg else (255, 255, 255)
    return mask, detected


def build_dual_title(original_ttl1_bytes: bytes,
                     text_mask: list[bool],
                     text_color: tuple[int, int, int]):
    """Return (new_ttl1_bytes, new_ttl2_bytes)."""
    orig = ta2_codec.decode_ta2(original_ttl1_bytes)
    pixels = bytearray(orig["pixels"])
    palette = list(orig["palette"])
    w, h = orig["w"], orig["h"]

    if len(text_mask) != w * h:
        raise ValueError("text mask size doesn't match the original image size")

    # Pair the woman indices (0..7) with their hidden twins (8..14). For each
    # pixel:
    #   - If your text mask has content here, encode 8 + woman_idx. That index
    #     looks like the surrounding woman in DM_TTL1's palette but lights up
    #     white once DM_TTL2's palette takes over.
    #   - Otherwise encode the plain woman_idx. Visible in DM_TTL1's palette,
    #     black in DM_TTL2's palette.
    out = bytearray(w * h)
    for i in range(w * h):
        orig_idx = pixels[i]
        woman_idx = orig_idx if orig_idx <= 7 else orig_idx - 8
        out[i] = (8 + woman_idx) if text_mask[i] else woman_idx

    new_ttl1 = ta2_codec.encode_ta2(bytes(out), palette, w, h)

    # DM_TTL2 carries only the fade-target palette. Its pixel data is
    # immediately overwritten by DM_TTL1's decode. Black for the illustration
    # indices (0..7) and the requested colour for the text indices (8..14).
    ttl2_palette: list[tuple[int, int, int]] = [(0, 0, 0)] * 256
    for i in range(8, 15):
        ttl2_palette[i] = text_color
    dummy = bytes(w * h)
    new_ttl2 = ta2_codec.encode_ta2(dummy, ttl2_palette, w, h)

    return new_ttl1, new_ttl2


def save_preview(ttl1_bytes: bytes, ttl2_bytes: bytes, out_dir: Path):
    """Render what the screen looks like with DM_TTL1's pixels under each
    of the two palettes. Useful for sanity-checking before you patch."""
    d1 = ta2_codec.decode_ta2(ttl1_bytes)
    d2 = ta2_codec.decode_ta2(ttl2_bytes)

    img1 = Image.frombytes("P", (d1["w"], d1["h"]), d1["pixels"])
    pal1 = []
    for r, g, b in d1["palette"]:
        pal1.extend([r, g, b])
    img1.putpalette(pal1)
    img1.save(out_dir / "_preview_phase1.png")

    img2 = Image.frombytes("P", (d1["w"], d1["h"]), d1["pixels"])
    pal2 = []
    for r, g, b in d2["palette"]:
        pal2.extend([r, g, b])
    img2.putpalette(pal2)
    img2.save(out_dir / "_preview_phase2.png")


def main():
    ap = argparse.ArgumentParser(
        description="Build a dual-image title-screen pair.")
    ap.add_argument("--original-ttl1", required=True,
                    help="path to the original DM_TTL1.TA2 (provides the illustration)")
    ap.add_argument("--text-png", required=True,
                    help="640x480 PNG containing the new text mask (non-bg pixels become text)")
    ap.add_argument("--text-color", default=None,
                    help="phase-2 text colour as #RRGGBB, default: most common non-bg colour in the PNG")
    ap.add_argument("-o", "--out-dir", default=".",
                    help="output directory (default: current dir)")
    ap.add_argument("--no-preview", dest="preview", action="store_false",
                    default=True, help="skip writing _preview_phase*.png")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    orig_bytes = Path(args.original_ttl1).read_bytes()
    mask, detected_color = png_to_text_mask(Path(args.text_png))

    if args.text_color:
        h = args.text_color.lstrip("#")
        if len(h) != 6:
            raise SystemExit("--text-color must be a 6-digit hex value (e.g. #ffffff)")
        text_color = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    else:
        text_color = detected_color

    print(f"text colour (phase 2): RGB{text_color}")
    print(f"text mask coverage:    {sum(mask)} of {len(mask)} pixels "
          f"({100 * sum(mask) / len(mask):.2f}%)")

    new_ttl1, new_ttl2 = build_dual_title(orig_bytes, mask, text_color)

    p1 = out_dir / "DM_TTL1.TA2"
    p2 = out_dir / "DM_TTL2.TA2"
    p1.write_bytes(new_ttl1)
    p2.write_bytes(new_ttl2)
    print(f"wrote {p1}  ({len(new_ttl1)} bytes)")
    print(f"wrote {p2}  ({len(new_ttl2)} bytes)")

    if args.preview:
        save_preview(new_ttl1, new_ttl2, out_dir)
        print("wrote _preview_phase1.png and _preview_phase2.png")


if __name__ == "__main__":
    main()
