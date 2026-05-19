TA2 Image Tools for Ningyou Tsukai / Metal & Lace
=================================================

Custom utilities for decoding and re-encoding the game's TA2 graphics
format. Written for the "Metal & Lace" English Translation Patch on
the FM Towns by Derek Pascarella (ateam).


Requirements
------------
Python 3.10 or newer, plus Pillow:

    pip install Pillow


Files
-----
ta2_codec.py
    Pure-Python library implementing the TA2 image format used by the
    game. Imported by the other scripts; not run directly.

ta2_decode.py
    Decodes TA2 (and AS2) files from the game into 8-bit PNG. Use this
    first to get editable copies of the originals.

ta2_encode.py
    Encodes a 640x480 PNG into a single TA2 file. Suitable for any
    standalone full-screen image the game loads (FOREST.TA2, OPTXT2T.TA2,
    GA_F.TA2, etc.).

ta2_dual_title.py
    Builds a replacement title screen. The original title is encoded
    across DM_TTL1.TA2 (illustration) and DM_TTL2.TA2 (palette-only fade
    target), with both contributing to a single dual-image pixel buffer.
    This script preserves that structure so the illustration still fades
    smoothly into your replacement text.


Workflow
--------
1. Extract the disc image's contents to a folder so you can read the
   original VISUAL\*.TA2 files. Tools like CDmage or bchunk can pull the
   files out of a .bin/.cue or .iso; the exact procedure depends on
   which disc image format you have.

2. Decode the originals to PNGs so you have something to edit. For
   example, to decode every TA2 in the VISUAL folder:

       python ta2_decode.py path/to/extracted/VISUAL/*.TA2 -o decoded

   The decoded PNGs are 8-bit indexed and match what the game renders
   on screen.

3. Edit the PNG(s) in any image editor. Keep the size at 640x480, and
   for best results stay in 8-bit indexed mode. If you save as RGB the
   encoder will quantise back down to 256 colours automatically, which
   is usually fine for stylised art but may not be for photographic
   content.

4. Re-encode. For a standalone image (e.g. you want to replace the
   "SILHOUETTE" intro text or one of the gameplay backdrops):

       python ta2_encode.py your_image.png -o out

   For the title screen, use the dual-title tool instead so the
   illustration's fade-into-text effect keeps working:

       python ta2_dual_title.py \
           --original-ttl1 path/to/extracted/VISUAL/DM_TTL1.TA2 \
           --text-png      your_title_text.png \
           --text-color    "#ffffff" \
           -o out

   The dual-title tool needs the unmodified original DM_TTL1.TA2 as
   input because it reuses the woman illustration that's encoded in it.

5. Splice the new TA2 file(s) back into your disc image at the paths
   the game uses (\VISUAL\DM_TTL1.TA2, \VISUAL\DM_TTL2.TA2, etc.).

   For flat .iso images (2048-byte sectors) most CD-replace tools work.
   For raw .bin/.cue images (2352-byte sectors with sync headers and
   EDC/ECC) you must use a tool that understands the raw sector format.
   Writing the file's bytes linearly into a raw .bin will overflow into
   the next sector's sync header and corrupt the disc.


Notes
-----
- The encoder mirrors the codec settings every original TA2 in the game
  uses (header byte 0x19 = 0x01, alphabet bitmap mode). Files produced
  by this tool decode identically in the real game and in Tsugaru.

- ta2_dual_title.py can only produce a single-colour phase-2 text. The
  encoding trick used by the game ties each text pixel's palette index
  to the illustration shade underneath it, so a gradient text isn't
  possible within this format.

- ta2_encode.py and ta2_dual_title.py round-trip their output through
  the decoder and verify the pixels match the source PNG before they
  finish, so a successful run is your guarantee that the file is
  well-formed.
