"""
ta2_codec.py
Decoder and encoder for the TA2 image format used by Forest's "Ningyou Tsukai"
(FM Towns, 1993, localized as "Metal & Lace").

This is a library module, it isn't meant to be run directly. Import it from
ta2_encode.py, ta2_dual_title.py, or your own script.


Format notes
------------
A TA2 file is laid out as:

    0x00..0x03   magic "TA2\\0"
    0x04..0x07   file size (uint32 LE)
    0x08..0x0B   X start offset, in bytes within the destination scanline
    0x0C..0x0F   Y start offset, in scanlines
    0x10..0x13   image width  in pixels (uint32 LE)
    0x14..0x17   image height in scanlines
    0x18         flag byte. Bit 7 set means a 256-entry palette follows.
    0x19         codec-mode byte. Bit 0 selects between two count readers
                 (see read_count below).
    0x1A         literal-bit-width hint. The codec uses the position of the
                 highest set bit. 0x80+ means raw 8-bit byte literals (no
                 alphabet bitmap).
    0x1B..0x1F   reserved (zero in all known files).
    0x20..0x31F  optional 256-entry palette, 3 bytes per entry, in GRB order
                 (matches the FM Towns 256-colour DAC port mapping: byte 0
                 goes to port 0xFD96 (G), byte 1 to 0xFD94 (R), byte 2 to
                 0xFD92 (B)).
    rest of file compressed bitstream.

The bitstream is read in 32-bit little-endian dwords. Bits are consumed
from the dword's MSB downwards. Every reader inside the codec uses this
convention, so the high bit of the first byte (LE) of each 4-byte chunk is
the first bit out.

The compressed payload begins with a small header that describes a Huffman
tree, then optionally a 256-bit "alphabet bitmap", then the per-scanline
codes:

    5 bits           N-1, the alphabet size (1..32 symbols)
    N * 5 bits       per-symbol "code length" values. These aren't Huffman
                     bit-lengths, they're action keys into the static
                     dispatch table at exe va 0x37CC8. Keys are:
                         0    literal byte
                         1    run-length (repeat previous byte, count
                              read via read_count)
                         2    back-ref (-1,  0)
                         3    back-ref (-1, -1)
                         4    back-ref (-1, +1)
                         5    back-ref ( 0, -2)
                         6    back-ref (-2,  0)
                         7    back-ref (-2, -2)
                         8    back-ref (-2, +2)
                         9    back-ref ( 0, -4)
                        10    back-ref (-4,  0)
                        11    back-ref (-4, -4)
                        12    back-ref (-4, +4)
                        13    back-ref ( 0, -8)
                        14    back-ref (-8,  0)
                        15    back-ref (-8, -8)
                        16    back-ref (-8, +8)
                        17    back-ref ( 0,-16)
                        18    back-ref (-16, 0)
                        19    back-ref (-16,-16)
                        20    back-ref (-16,+16)
                     Back-refs and run-length each read an additional count
                     value via read_count.
    5 bits           "post-table flag". 0 means the tree has a single leaf,
                     the next 5 bits give that leaf's symbol index. Non-zero
                     means there's a multi-leaf tree, encoded in pre-order
                     using the format described in build_tree_from_tokens.

If header byte 0x1A is below 0x80, a 256-bit alphabet bitmap follows the
tree. Each bit i, in order, says whether byte value i is present in the
image (bit=0) or absent (bit=1). The "alphabet" is the ordered list of
present values. Literal actions read literal_bits bits as an index into it,
where literal_bits is the bit-length of header byte 0x1A. If 0x1A >= 0x80
the bitmap is skipped and literal actions read 8 bits as a raw byte value.

The image data is decoded one scanline at a time. The codec keeps a
remaining-pixel counter that starts at the image width. Each action
consumes one Huffman code from the bitstream, performs its work, and
decrements the counter by the number of pixels written. When the counter
hits zero the scanline is complete.
"""

from __future__ import annotations
import struct
from dataclasses import dataclass
from collections import Counter


# Back-ref offsets indexed by action key, as encoded in the dispatch table
# at exe va 0x37CC8 (16 entries x 8 bytes, two signed dwords each). Keys 0
# and 1 don't use offsets (literal and run-length respectively).
ACTION_TABLE = {
    0:  (None, None),
    1:  (None, None),
    2:  (-1, 0),
    3:  (-1, -1),
    4:  (-1, +1),
    5:  (0, -2),
    6:  (-2, 0),
    7:  (-2, -2),
    8:  (-2, +2),
    9:  (0, -4),
    10: (-4, 0),
    11: (-4, -4),
    12: (-4, +4),
    13: (0, -8),
    14: (-8, 0),
    15: (-8, -8),
    16: (-8, +8),
    17: (0, -16),
    18: (-16, 0),
    19: (-16, -16),
    20: (-16, +16),
}


# ----------------------------------------------------------------------------
# Bit-stream reader
# ----------------------------------------------------------------------------

class BitReader:
    """MSB-first reader over a little-endian dword stream.

    Loads 4 bytes at a time as a uint32 LE, then yields bits from the high
    end via `(buf >> 31) & 1` followed by a left shift. This matches the
    `add ebp, ebp` shift used throughout the runtime decoder.
    """

    def __init__(self, data: bytes, byte_offset: int = 0):
        self.data = data
        self.byte_offset = byte_offset
        self.bit_buf = 0
        self.bits_left = 0
        self.bits_consumed = 0

    def _refill(self):
        if self.byte_offset + 4 > len(self.data):
            raise EOFError("bit stream exhausted")
        self.bit_buf = int.from_bytes(self.data[self.byte_offset:self.byte_offset + 4], "little")
        self.byte_offset += 4
        self.bits_left = 32

    def read_bits(self, n: int) -> int:
        v = 0
        for _ in range(n):
            if self.bits_left == 0:
                self._refill()
            v = (v << 1) | ((self.bit_buf >> 31) & 1)
            self.bit_buf = (self.bit_buf << 1) & 0xFFFFFFFF
            self.bits_left -= 1
            self.bits_consumed += 1
        return v

    def read5(self) -> int:
        return self.read_bits(5)

    def read8(self) -> int:
        return self.read_bits(8)

    def read_count(self, alt: bool = False) -> int:
        """Read a positive count using one of two Elias-style variants. Which
        variant is in effect is determined by bit 0 of header byte 0x19.

        alt=False (header 0x19 bit 0 = 0, runtime sub_38574):
            k zero bits, a '1', then k payload bits.
            count = 2^k + payload.
            Ranges: 1 / 2..3 / 4..7 / 8..15 / ...

        alt=True (header 0x19 bit 0 = 1, runtime sub at 0x388A8):
            k-1 zero bits, a '1', then k payload bits.
            count = (2^k - 1) + payload.
            Ranges: 1..2 / 3..6 / 7..14 / 15..30 / ...

        Every TA2 in the shipped game uses alt=True.
        """
        leading_zeros = 0
        while True:
            if self.read_bits(1) == 1:
                break
            leading_zeros += 1

        if not alt:
            payload = 0
            for _ in range(leading_zeros):
                payload = (payload << 1) | self.read_bits(1)
            return (1 << leading_zeros) + payload

        k = leading_zeros + 1
        payload = 0
        for _ in range(k):
            payload = (payload << 1) | self.read_bits(1)
        return ((1 << k) - 1) + payload


# ----------------------------------------------------------------------------
# Bit-stream writer (inverse of BitReader)
# ----------------------------------------------------------------------------

class BitWriter:
    """Packs bits MSB-first into 32-bit little-endian dwords."""

    def __init__(self):
        self.dwords: list[int] = []
        self.cur = 0
        self.bits_in_cur = 0

    def write_bits(self, value: int, n: int):
        for i in range(n - 1, -1, -1):
            bit = (value >> i) & 1
            self.cur = (self.cur << 1) | bit
            self.bits_in_cur += 1
            if self.bits_in_cur == 32:
                self.dwords.append(self.cur)
                self.cur = 0
                self.bits_in_cur = 0

    def write5(self, v: int):
        self.write_bits(v, 5)

    def write8(self, v: int):
        self.write_bits(v, 8)

    def write_count(self, n: int, alt: bool = False):
        """Inverse of BitReader.read_count for the same `alt` selector."""
        assert n >= 1
        if not alt:
            k = n.bit_length() - 1
            payload = n - (1 << k)
            for _ in range(k):
                self.write_bits(0, 1)
            self.write_bits(1, 1)
            for i in range(k - 1, -1, -1):
                self.write_bits((payload >> i) & 1, 1)
            return

        k = (n + 1).bit_length() - 1
        payload = n - ((1 << k) - 1)
        for _ in range(k - 1):
            self.write_bits(0, 1)
        self.write_bits(1, 1)
        for i in range(k - 1, -1, -1):
            self.write_bits((payload >> i) & 1, 1)

    def finish(self) -> bytes:
        # Pad the final dword with zeros. The runtime decoder may read these
        # bits but won't act on them: it stops once each scanline's pixel
        # counter reaches zero.
        while self.bits_in_cur != 0:
            self.cur = (self.cur << 1) & 0xFFFFFFFF
            self.bits_in_cur += 1
            if self.bits_in_cur == 32:
                self.dwords.append(self.cur)
                self.cur = 0
                self.bits_in_cur = 0
        out = bytearray()
        for d in self.dwords:
            out += d.to_bytes(4, "little")
        return bytes(out)


# ----------------------------------------------------------------------------
# Huffman tree
# ----------------------------------------------------------------------------

@dataclass
class Node:
    is_leaf: bool
    symbol: int = -1
    left: "Node | None" = None
    right: "Node | None" = None
    n_branches: int = 0     # internal-node count of this subtree


def build_tree_from_tokens(reader: BitReader) -> Node:
    """Parse the codec's pre-order tree encoding.

    Tokens are 5 bits each. The first one is the post-table flag:
        0    the tree is just one leaf, the next 5 bits give its symbol idx.
        > 0  the tree has at least one branch, recurse into emit_branch.

    Inside an internal node we read T_left then T_right. T == 0 means the
    child is a leaf whose symbol idx is the following 5 bits. T > 0 means
    the child is an internal node and T is the count of internal nodes in
    that subtree (the runtime uses T to compute the JIT-emitted jb offset
    as 25*T + 10 bytes).
    """
    flag = reader.read5()
    if flag == 0:
        return Node(is_leaf=True, symbol=reader.read5())

    def emit_branch() -> Node:
        t_left = reader.read5()
        if t_left == 0:
            left = Node(is_leaf=True, symbol=reader.read5())
        else:
            left = emit_branch()

        t_right = reader.read5()
        if t_right == 0:
            right = Node(is_leaf=True, symbol=reader.read5())
        else:
            right = emit_branch()

        return Node(is_leaf=False, left=left, right=right,
                    n_branches=1 + left.n_branches + right.n_branches)

    return emit_branch()


def count_branches(node: Node) -> int:
    if node.is_leaf:
        return 0
    assert node.left is not None and node.right is not None
    return 1 + count_branches(node.left) + count_branches(node.right)


def emit_tree_to_tokens(root: Node, writer: BitWriter, post_flag_value: int = 1):
    """Inverse of build_tree_from_tokens.

    post_flag_value can be any non-zero 5-bit number when the tree has at
    least one branch (the runtime doesn't use the value, only its zero/
    non-zero state). Convention is to use the tree's internal-node count.
    """
    if root.is_leaf:
        writer.write5(0)
        writer.write5(root.symbol)
        return

    writer.write5(post_flag_value)

    def emit(node: Node):
        assert node.left is not None and node.right is not None
        if node.left.is_leaf:
            writer.write5(0)
            writer.write5(node.left.symbol)
        else:
            writer.write5(node.left.n_branches)
            emit(node.left)
        if node.right.is_leaf:
            writer.write5(0)
            writer.write5(node.right.symbol)
        else:
            writer.write5(node.right.n_branches)
            emit(node.right)

    emit(root)


def tree_to_codes(root: Node) -> dict[int, str]:
    """Walk the tree and return a mapping of symbol -> Huffman bit-string."""
    codes: dict[int, str] = {}

    def walk(n: Node, prefix: str):
        if n.is_leaf:
            codes[n.symbol] = prefix or "0"
            return
        assert n.left is not None and n.right is not None
        walk(n.left, prefix + "0")
        walk(n.right, prefix + "1")

    walk(root, "")
    return codes


# ----------------------------------------------------------------------------
# Decoder
# ----------------------------------------------------------------------------

def decode_ta2(file_bytes: bytes) -> dict:
    """Decode a TA2 (or AS2) file.

    Returns a dict with:
        palette        list of 256 (R, G, B) tuples, or None if absent
        pixels         bytes, length width*height (8-bit indexed)
        w, h           image dimensions
        xoff, yoff     header X/Y offsets (usually 0)
        flag18         header byte 0x18
        mode19         header byte 0x19
        mode1A         header byte 0x1A
        code_lengths   the per-symbol action keys
        tree           the parsed Huffman tree root
    """
    magic = file_bytes[0:4]
    if magic not in (b"TA2\0", b"AS2\0"):
        raise ValueError(f"bad magic {magic!r}")

    x_off  = struct.unpack("<I", file_bytes[0x08:0x0C])[0]
    y_off  = struct.unpack("<I", file_bytes[0x0C:0x10])[0]
    width  = struct.unpack("<I", file_bytes[0x10:0x14])[0]
    height = struct.unpack("<I", file_bytes[0x14:0x18])[0]
    flag18 = file_bytes[0x18]
    mode19 = file_bytes[0x19]
    mode1A = file_bytes[0x1A]
    has_pal = bool(flag18 & 0x80)

    # Palette (GRB order on disc).
    palette = None
    pos = 0x20
    if has_pal:
        palette = []
        for i in range(256):
            g = file_bytes[pos + i * 3 + 0]
            r = file_bytes[pos + i * 3 + 1]
            b = file_bytes[pos + i * 3 + 2]
            palette.append((r, g, b))
        pos += 768

    br = BitReader(file_bytes, pos)

    # Alphabet size and per-symbol action keys.
    n_syms = br.read5() + 1
    code_lengths = [br.read5() for _ in range(n_syms)]

    # Huffman tree.
    root = build_tree_from_tokens(br)

    # Optional alphabet bitmap. The literal handler reads literal_bits bits
    # as an alphabet index when the bitmap is present. Otherwise it reads a
    # full byte.
    alphabet: list[int] | None = None
    literal_bits = 8
    if mode1A < 0x80:
        alphabet = []
        for v in range(256):
            if br.read_bits(1) == 0:
                alphabet.append(v)
        literal_bits = max(1, mode1A.bit_length())

    alt_count = bool(mode19 & 1)

    # Decode all scanlines into a framebuffer with the game's 1024-byte
    # stride so back-references resolve to the same offsets the runtime
    # decoder would use.
    pitch = 0x400
    fb = bytearray(pitch * (height + y_off))
    edi_base = y_off * pitch + x_off

    for line in range(height):
        edi = edi_base + line * pitch
        eax = width
        prev_byte = 0

        while eax > 0:
            node = root
            while not node.is_leaf:
                bit = br.read_bits(1)
                node = node.right if bit else node.left
                assert node is not None
            ak = code_lengths[node.symbol]

            if ak == 0:
                # Literal byte (alphabet index, or raw byte if no bitmap).
                idx = br.read_bits(literal_bits)
                v = alphabet[idx] if alphabet is not None else idx
                fb[edi] = v
                edi += 1
                prev_byte = v
                eax -= 1

            elif ak == 1:
                # Run-length: repeat the previously written byte.
                count = br.read_count(alt=alt_count)
                copy = min(count, eax)
                for _ in range(copy):
                    fb[edi] = prev_byte
                    edi += 1
                eax -= copy

            elif 2 <= ak <= 20:
                # Back-reference: copy from (dy, dx) earlier in the FB.
                dy, dx = ACTION_TABLE[ak]
                assert dy is not None and dx is not None
                offset = dy * pitch + dx
                count = br.read_count(alt=alt_count)
                copy = min(count, eax)
                src = edi + offset
                for _ in range(copy):
                    fb[edi] = fb[src]
                    edi += 1
                    src += 1
                    prev_byte = fb[edi - 1]
                eax -= copy

            else:
                raise ValueError(f"unknown action key {ak}")

    # Extract the visible region from the framebuffer.
    pixels = bytearray(width * height)
    for y in range(height):
        src = (y_off + y) * pitch + x_off
        pixels[y * width:(y + 1) * width] = fb[src:src + width]

    return dict(palette=palette, pixels=bytes(pixels), w=width, h=height,
                xoff=x_off, yoff=y_off,
                flag18=flag18, mode19=mode19, mode1A=mode1A,
                code_lengths=code_lengths, tree=root)


# ----------------------------------------------------------------------------
# Encoder
# ----------------------------------------------------------------------------

def encode_ta2(pixels: bytes, palette: list[tuple[int, int, int]],
               width: int, height: int,
               x_off: int = 0, y_off: int = 0,
               pitch: int = 0x400) -> bytes:
    """Encode an 8-bit indexed image as a TA2 file.

    Header bytes are set to mirror every shipped TA2:
        0x18 = 0x80     palette present
        0x19 = 0x01     alternate (alt=True) count reader
        0x1A = N        N has the bit-length needed to address the alphabet

    The Huffman tree has three symbols: literal, run-length, and a single
    back-reference one scanline up. Codes are assigned by action frequency,
    so the most common action gets the 1-bit code.
    """
    if len(pixels) != width * height:
        raise ValueError(f"pixel buffer length {len(pixels)} != w*h ({width * height})")
    if len(palette) > 256:
        raise ValueError("palette has more than 256 entries")

    # Build alphabet (sorted byte values that appear in pixels). Force 0 to
    # be present so the back-ref-from-blank-area case has a valid index.
    used = sorted(set(pixels))
    if 0 not in used:
        used = [0] + used
    alphabet_size = len(used)
    byte_to_idx = {v: i for i, v in enumerate(used)}

    literal_bits = max(1, (alphabet_size - 1).bit_length()) if alphabet_size > 1 else 1
    mode1A = 1 << (literal_bits - 1)
    assert mode1A < 0x80, "alphabet too large, would force raw-byte literal mode"

    # Header (32 bytes, file size patched at the end).
    header = bytearray(32)
    header[0:4] = b"TA2\0"
    header[0x08:0x0C] = x_off.to_bytes(4, "little")
    header[0x0C:0x10] = y_off.to_bytes(4, "little")
    header[0x10:0x14] = width.to_bytes(4, "little")
    header[0x14:0x18] = height.to_bytes(4, "little")
    header[0x18] = 0x80
    header[0x19] = 0x01
    header[0x1A] = mode1A

    # Palette, written in GRB order to match the DAC port mapping.
    pal_bytes = bytearray(768)
    for i, (r, g, b) in enumerate(palette):
        pal_bytes[i * 3 + 0] = g
        pal_bytes[i * 3 + 1] = r
        pal_bytes[i * 3 + 2] = b

    # Plan a per-scanline action list. For each pixel, pick the better of:
    #   BRUP   back-reference one line up (only allowed from line 1 onward,
    #          see note below)
    #   RLE    a literal followed by a run-length over identical pixels
    #   LIT    a single literal byte
    #
    # Line 0 must NOT use BRUP. The runtime back-ref reads from edi - pitch,
    # which points before the framebuffer's start.
    plan: list[list[tuple[str, int, int]]] = []
    prev_line = bytes(pitch)

    for y in range(height):
        line = pixels[y * width:(y + 1) * width]
        actions: list[tuple[str, int, int]] = []
        allow_brup = (y > 0)
        i = 0
        while i < width:
            br_len = 0
            if allow_brup:
                while i + br_len < width and line[i + br_len] == prev_line[i + br_len]:
                    br_len += 1

            rle_len = 0
            while i + rle_len < width and line[i + rle_len] == line[i]:
                rle_len += 1

            if br_len >= rle_len and br_len >= 2:
                actions.append(("BRUP", br_len, 0))
                i += br_len
            elif rle_len >= 2:
                actions.append(("LIT", 1, line[i]))
                actions.append(("RLE", rle_len - 1, 0))
                i += rle_len
            else:
                actions.append(("LIT", 1, line[i]))
                i += 1

        plan.append(actions)
        prev_line = bytes(line) + bytes(pitch - width)

    # Order symbols by frequency so the most common action gets "0".
    freq = Counter(a[0] for line_acts in plan for a in line_acts)
    sorted_actions = sorted(["LIT", "RLE", "BRUP"], key=lambda a: -freq.get(a, 0))
    action_to_code = {
        sorted_actions[0]: "0",
        sorted_actions[1]: "10",
        sorted_actions[2]: "11",
    }
    sym_of_action = {"LIT": 0, "RLE": 1, "BRUP": 2}    # action key per symbol slot
    action_key_of = {"LIT": 0, "RLE": 1, "BRUP": 2}

    bw = BitWriter()

    # 5 bits N-1, then N action keys.
    N = 3
    bw.write5(N - 1)
    for sym in range(N):
        action = ["LIT", "RLE", "BRUP"][sym]
        bw.write5(action_key_of[action])

    # Post-table flag (non-zero -> tree has a branch, runtime ignores value).
    bw.write5(2)

    # Tree pre-order, matching the shape root -> (leaf, branch -> (leaf, leaf)).
    bw.write5(0); bw.write5(sym_of_action[sorted_actions[0]])
    bw.write5(1)
    bw.write5(0); bw.write5(sym_of_action[sorted_actions[1]])
    bw.write5(0); bw.write5(sym_of_action[sorted_actions[2]])

    # 256-bit alphabet bitmap.
    bitmap = [1] * 256
    for v in used:
        bitmap[v] = 0
    for b in bitmap:
        bw.write_bits(b, 1)

    # Scanline payload.
    for line_acts in plan:
        for act_name, count, byte_val in line_acts:
            for c in action_to_code[act_name]:
                bw.write_bits(int(c), 1)
            if act_name == "LIT":
                bw.write_bits(byte_to_idx[byte_val], literal_bits)
            elif act_name == "RLE":
                bw.write_count(count, alt=True)
            elif act_name == "BRUP":
                bw.write_count(count, alt=True)

    bit_data = bw.finish()
    out = bytearray(header)
    out += pal_bytes
    out += bit_data
    out[4:8] = len(out).to_bytes(4, "little")
    return bytes(out)
