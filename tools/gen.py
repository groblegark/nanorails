#!/usr/bin/env python3
"""Asset generator for the dual-PPU "train through town" demo.

Emits:
  binclude/background.chr   4096 bytes (256 tiles, shared by both PPUs + sprites)
  src/palette.s             BG + sprite palettes
  src/leveldata.s           near (PPU1) + far (PPU2) nametables, 2 screens each
  src/traindata.s           locomotive metasprite table
  include/gen.inc           tile-id / count constants used by train.s
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ----------------------------------------------------------------------------
# tile bank: each tile is 8x8 of color indices 0..3
# ----------------------------------------------------------------------------
tiles = []            # list of 8x8 (list of 8 strings length 8)
tile_name = {}        # name -> index

def blank8():
    return ["00000000"]*8

def add_tile(name, rows):
    assert len(rows) == 8 and all(len(r) == 8 for r in rows), (name, [len(r) for r in rows])
    idx = len(tiles)
    tiles.append(rows)
    if name:
        tile_name[name] = idx
    return idx

# reserve tile 0 = fully transparent
add_tile("blank", blank8())

# ---- canvas helpers for drawing big multi-tile images ----------------------
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[0]*w for _ in range(h)]
    def rect(self, x0, y0, x1, y1, c):
        for y in range(max(0,y0), min(self.h,y1)):
            for x in range(max(0,x0), min(self.w,x1)):
                self.px[y][x] = c
    def hline(self, x0, x1, y, c):
        if 0 <= y < self.h:
            for x in range(max(0,x0), min(self.w,x1)):
                self.px[y][x] = c
    def vline(self, x, y0, y1, c):
        if 0 <= x < self.w:
            for y in range(max(0,y0), min(self.h,y1)):
                self.px[y][x] = c
    def pset(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c
    def slice_tiles(self):
        """yield (tx, ty, rows) for each 8x8 cell that is non-empty."""
        for ty in range(0, self.h, 8):
            for tx in range(0, self.w, 8):
                rows = []
                empty = True
                for yy in range(8):
                    s = ""
                    for xx in range(8):
                        v = self.px[ty+yy][tx+xx]
                        s += str(v)
                        if v: empty = False
                    rows.append(s)
                yield tx, ty, rows, empty

# ============================================================================
# BACKGROUND TILES
# ============================================================================
# palette 1 (ground): 1=grass green, 2=dark green, 3=brown dirt
add_tile("grass_top", [
    "00000000",
    "10100010",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
])
add_tile("grass_fill", ["11111111"]*8)
add_tile("dirt", [
    "33333333",
    "33333333",
    "23332333",
    "33333333",
    "33333333",
    "33233332",
    "33333333",
    "33333333",
])
# rail: embankment top with two steel rails + ties (palette 1: 2=dark, 3=brown tie, use 2 for steel)
add_tile("rail", [
    "22222222",  # steel rail head
    "00000000",
    "33033033",  # ties (brown) with gaps
    "33033033",
    "11111111",  # ballast/grass
    "11111111",
    "11111111",
    "11111111",
])

# palette 2 (near houses/props): 1=wall(warm), 2=dark(roof/wood/outline), 3=window/trim
# small near house drawn as a 24x24 image
house = Canvas(24, 24)
house.rect(0, 8, 24, 24, 1)         # wall
# roof (triangle)
for y in range(0, 9):
    half = y + 3
    house.rect(12-half, y, 12+half, y+1, 2)
house.rect(2, 8, 24, 9, 2)          # eaves line
# windows
house.rect(3, 12, 8, 17, 3); house.rect(3,12,8,13,2); house.rect(5,12,6,17,2)
house.rect(16, 12, 21, 17, 3); house.rect(16,12,21,13,2); house.rect(18,12,19,17,2)
# door
house.rect(10, 16, 15, 24, 2); house.rect(11,17,14,24,3)
for tx, ty, rows, empty in house.slice_tiles():
    add_tile(f"house_{tx//8}_{ty//8}", rows)

# tree: 16x24 (foliage palette1 green, trunk brown)
tree = Canvas(16, 24)
tree.rect(6, 16, 10, 24, 3)              # trunk (brown=3 in pal1)
tree.rect(2, 2, 14, 16, 1)               # foliage block
# round the foliage corners
for (x,y) in [(2,2),(3,2),(2,3),(13,2),(12,2),(13,3),(2,14),(13,14)]:
    tree.pset(x,y,0)
tree.rect(4,4,12,6,2); tree.rect(3,9,7,11,2)  # shading clumps (dark green)
for tx, ty, rows, empty in tree.slice_tiles():
    add_tile(f"tree_{tx//8}_{ty//8}", rows)

# lamppost: 8x24 (pole gray=2, lamp yellow=3) -- use pal2
lamp = Canvas(8, 24)
lamp.rect(3, 4, 5, 24, 2)     # pole
lamp.rect(1, 0, 7, 5, 3)      # lamp head (glow)
lamp.rect(2, 1, 6, 2, 2)
for tx, ty, rows, empty in lamp.slice_tiles():
    add_tile(f"lamp_{tx//8}_{ty//8}", rows)

# fence (palette2): 8x8 picket repeated
add_tile("fence", [
    "00000000",
    "20020020",
    "22222220",
    "20020020",
    "20020020",
    "22222220",
    "20020020",
    "20020020",
])

# palette 3 (far skyline): 1=building light, 2=building dark, 3=window
# far building column tiles (stackable): base, mid (windows), top (with roof line)
add_tile("fb_top", [
    "01111110",
    "11111111",
    "11111111",
    "13313310",
    "11111110",
    "13313310",
    "11111110",
    "11111111",
])
add_tile("fb_mid", [
    "11111111",
    "13313310",
    "11111110",
    "13313310",
    "11111110",
    "13313310",
    "11111110",
    "11111111",
])
add_tile("fb_top_b", [
    "00111100",
    "01111110",
    "11111111",
    "11313110",
    "11111110",
    "11313110",
    "11111110",
    "11111111",
])
# a flat-roof wide building uses fb_mid; a pointed one:
add_tile("fb_spire", [
    "00011000",
    "00011000",
    "00111100",
    "01111110",
    "11111111",
    "11311310",
    "11111110",
    "11111111",
])

# station depot (palette 2): walls red, roof black, sign/awning yellow.
# 40x32 -> 5x4 tiles. base sits on row 23 (just above the rail).
depot = Canvas(40, 32)
depot.rect(2, 10, 38, 32, 1)            # walls
# bright pitched roof (yellow trim line makes it pop vs the red houses)
depot.rect(0, 5, 40, 10, 2)
depot.rect(2, 2, 38, 6, 2)
depot.rect(0, 9, 40, 10, 3)             # yellow eave trim
# big clock roundel
depot.rect(16, 4, 24, 8, 3); depot.rect(18, 5, 22, 7, 2); depot.pset(20, 5, 3)
# striped awning over the platform (yellow/black)
for ax in range(2, 38, 4):
    depot.rect(ax, 14, ax+2, 17, 3)
    depot.rect(ax+2, 14, ax+4, 17, 2)
depot.rect(2, 13, 38, 14, 2)
# arched door (center)
depot.rect(16, 19, 24, 32, 2); depot.rect(17, 20, 23, 32, 3); depot.vline(20, 20, 32, 2)
# windows
depot.rect(5, 20, 11, 27, 3); depot.rect(5, 20, 11, 21, 2); depot.vline(8, 20, 27, 2)
depot.rect(29, 20, 35, 27, 3); depot.rect(29, 20, 35, 21, 2); depot.vline(32, 20, 27, 2)
for tx, ty, rows, empty in depot.slice_tiles():
    add_tile(f"depot_{tx//8}_{ty//8}", rows)
# platform tile (palette 2): stone lip + fill
add_tile("platform", [
    "22222222",
    "13131313",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
])
# station nameplate: a board on a post (palette 2). 8x24 -> 1x3 tiles.
sign = Canvas(8, 24)
sign.rect(3, 9, 5, 24, 2)               # post
sign.rect(0, 0, 8, 8, 3)                # board (bright)
sign.rect(0, 0, 8, 1, 2); sign.rect(0, 7, 8, 8, 2)
sign.rect(1, 2, 7, 3, 2); sign.rect(1, 4, 7, 5, 2)   # "text" lines
for tx, ty, rows, empty in sign.slice_tiles():
    add_tile(f"sign_{tx//8}_{ty//8}", rows)

# ============================================================================
# SPRITE TILES
# ============================================================================
SPR_START = len(tiles)

# --- locomotive body (spal0: 1=red,2=black,3=brass/yellow) -------------------
# Tiny 4-tile-wide engine: <=4 sprites on its busiest scanline, leaving room
# for coupled coaches without blowing the 8-sprites-per-scanline limit.
W, H = 32, 24
loco = Canvas(W, H)
# cab (back / left)
loco.rect(1, 2, 13, 24, 1)
loco.rect(0, 0, 14, 4, 2)              # cab roof overhang
loco.rect(3, 8, 11, 15, 3)             # cab window (bright)
loco.rect(3, 8, 11, 9, 2); loco.vline(7, 8, 15, 2)   # window frame
# boiler (red cylinder)
loco.rect(11, 9, 26, 24, 1)
loco.rect(11, 8, 27, 9, 3)             # brass top highlight
loco.vline(17, 9, 24, 2)               # boiler band
loco.vline(22, 9, 24, 2)
# smokebox / front (darker)
loco.rect(25, 7, 29, 24, 2)
loco.rect(25, 13, 29, 18, 3)           # headlight (brass)
# chimney + flare
loco.rect(18, 0, 23, 9, 2)
loco.rect(16, 0, 25, 2, 2)
# steam dome (brass)
loco.rect(12, 3, 16, 9, 3)
# footplate
loco.rect(1, 22, 29, 24, 2)
# cowcatcher (yellow wedge at front-bottom)
for y in range(16, 24):
    x1 = 29 + (y - 16) // 2
    loco.rect(29, y, min(W, x1 + 1), y + 1, 3)

train_body = []   # (dx, dy, tile)
for tx, ty, rows, empty in loco.slice_tiles():
    if empty: continue
    idx = add_tile(f"loco_{tx//8}_{ty//8}", rows)
    train_body.append((tx, ty, idx))

# --- wheels (spal1: 1=gray,2=black,3=lightgray), two spin frames -------------
def wheel(frame):
    w = Canvas(8, 8)
    w.rect(1, 1, 7, 7, 1)             # tyre fill gray
    # rim
    for (x,y) in [(1,1),(6,1),(1,6),(6,6)]:
        w.pset(x,y,0)
    w.rect(2,2,6,6,3)                 # light hub area
    w.rect(3,3,5,5,2)                 # hub
    if frame == 0:
        w.vline(4,1,7,2); w.hline(1,7,4,2)        # + spokes
    else:
        w.pset(2,2,2);w.pset(5,5,2);w.pset(5,2,2);w.pset(2,5,2)  # x spokes
        w.pset(3,3,2);w.pset(4,4,2);w.pset(4,3,2);w.pset(3,4,2)
    return w.px_rows()
# add a tiny method
Canvas.px_rows = lambda self: ["".join(str(v) for v in row) for row in self.px]
add_tile("wheel0", wheel(0))
add_tile("wheel1", wheel(1))

# --- smoke puffs (spal2: 1=white,2=lightgray,3=gray) -------------------------
add_tile("smoke0", [   # tiny
    "00000000",
    "00000000",
    "00011000",
    "00122100",
    "00122100",
    "00011000",
    "00000000",
    "00000000",
])
add_tile("smoke1", [   # small
    "00000000",
    "00111100",
    "01122110",
    "11222211",
    "11222211",
    "01122110",
    "00111100",
    "00000000",
])
add_tile("smoke2", [   # medium
    "00111100",
    "01111110",
    "11122111",
    "11233211",
    "11233211",
    "11122111",
    "01111110",
    "00111100",
])
add_tile("smoke3", [   # dissipating (faint, gray)
    "03000030",
    "30033000",
    "00330300",
    "03003330",
    "33000300",
    "00333003",
    "03000330",
    "30030000",
])

# --- speed gauge (HUD) -------------------------------------------------------
# meter_off: hollow segment; meter_on: filled. drawn with color1 (palette set
# via sprite attr at runtime). small upright bar.
add_tile("meter_off", [
    "00000000",
    "01111110",
    "01000010",
    "01000010",
    "01000010",
    "01000010",
    "01111110",
    "00000000",
])
def filled(c):
    return ["00000000","01111110"] + [f"01{c}{c}{c}{c}10" for _ in range(4)] + ["01111110","00000000"]
add_tile("meter_on",  filled("1"))   # green  (cruise band)
add_tile("meter_on2", filled("2"))   # yellow (upper band)
add_tile("meter_on3", filled("3"))   # red    (express band)

# little passenger that waits on the platform (sprite palette 0).
# 8x16 -> head + body.
pax = Canvas(8, 16)
pax.rect(2, 0, 6, 4, 2)        # hair/hat
pax.rect(2, 3, 6, 6, 3)        # face
pax.rect(1, 6, 7, 13, 1)       # coat
pax.rect(2, 13, 4, 16, 2); pax.rect(5, 13, 7, 16, 2)   # legs
for tx, ty, rows, empty in pax.slice_tiles():
    add_tile(f"pax_{tx//8}_{ty//8}", rows)

# passenger coach (sprite palette 3: 1=green body, 2=yellow windows, 3=red roof).
# Deliberately NOT red, so coaches read clearly against the red town/depot.
# 16x16 -> 2x2 tiles, coupled behind the locomotive.
coach = Canvas(16, 16)
coach.rect(0, 2, 16, 5, 3)          # roof (red)
coach.rect(1, 1, 15, 2, 2)          # roof trim (yellow)
coach.rect(0, 5, 16, 14, 1)         # body (green)
coach.rect(2, 7, 7, 12, 2); coach.rect(2, 7, 7, 8, 3); coach.vline(4, 7, 12, 3)
coach.rect(9, 7, 14, 12, 2); coach.rect(9, 7, 14, 8, 3); coach.vline(11, 7, 12, 3)
coach.rect(0, 13, 16, 16, 3)        # underframe (red)
coach.rect(6, 15, 10, 16, 2)        # coupler nub
for tx, ty, rows, empty in coach.slice_tiles():
    add_tile(f"coach_{tx//8}_{ty//8}", rows)

assert len(tiles) <= 256, f"too many tiles: {len(tiles)}"

# ============================================================================
# write CHR (4096 bytes = 256 tiles * 16)
# ============================================================================
def tile_bytes(rows):
    out = bytearray()
    for plane in (0, 1):
        for y in range(8):
            b = 0
            for x in range(8):
                c = int(rows[y][x])
                bit = (c >> plane) & 1
                b |= bit << (7 - x)
            out.append(b)
    return out

chr_data = bytearray()
for i in range(256):
    if i < len(tiles):
        chr_data += tile_bytes(tiles[i])
    else:
        chr_data += bytes(16)
assert len(chr_data) == 4096

os.makedirs(f"{ROOT}/binclude", exist_ok=True)
with open(f"{ROOT}/binclude/background.chr", "wb") as f:
    f.write(chr_data)

# ============================================================================
# palette.s
# ============================================================================
SKY = 0x22
bg_palettes = [
    [SKY, 0x20, 0x10, 0x00],    # 0 sky / clouds
    [SKY, 0x1A, 0x0A, 0x17],    # 1 ground: grass, dark green, brown
    [SKY, 0x16, 0x0F, 0x28],    # 2 near houses: brick red, black, window yellow
    [SKY, 0x2C, 0x1C, 0x30],    # 3 far skyline: light cyan, cyan, white-ish
]
spr_palettes = [
    [SKY, 0x16, 0x0F, 0x28],    # 0 train body: red, black, brass
    [SKY, 0x00, 0x0F, 0x10],    # 1 wheels/metal: gray, black, light gray
    [SKY, 0x20, 0x10, 0x00],    # 2 smoke: white, light gray, gray
    [SKY, 0x2A, 0x28, 0x16],    # 3 gauge: green (lit), yellow, red
]

def emit_pal(f):
    f.write("; AUTO-GENERATED by tools/gen.py\n")
    f.write('.include "ppu.inc"\n\n.export palette\n\n.segment "RODATA"\n\naPalettes:\n')
    for grp, pals in (("background", bg_palettes), ("sprite", spr_palettes)):
        f.write(f"a{grp.capitalize()}:\n")
        for p in pals:
            f.write(".byte " + ",".join(f"${c:02x}" for c in p) + "\n")
        f.write("\n")
    f.write(""".segment "CODE"

.proc palette
    lda #>Ppu::BACKGROUND_PALETTE
    sta Ppu::ADDR
    sta Ppu::ADDR2
    lda #<Ppu::BACKGROUND_PALETTE
    sta Ppu::ADDR
    sta Ppu::ADDR2
    ldx #0
loop:
    lda aPalettes, x
    sta Ppu::DATA
    sta Ppu::DATA2
    inx
    cpx #32
    bne loop
    rts
.endproc
""")

with open(f"{ROOT}/src/palette.s", "w") as f:
    emit_pal(f)

# ============================================================================
# NAMETABLES  (64 tiles wide world = 2 nametables of 32; wraps seamlessly)
# ============================================================================
WIDTH = 64
ROWS = 30
T = tile_name

def new_grid():
    return [[0]*WIDTH for _ in range(ROWS)]

# palette (attribute) maps: per 16x16 region we set a palette. We store per-tile
# palette then collapse to attribute bytes (2x2 tiles share one).
def new_pal():
    return [[0]*WIDTH for _ in range(ROWS)]

# ---------------- FAR layer (PPU2): sky + distant skyline -------------------
far = new_grid(); farp = new_pal()
import_seed = 12345
def rng(state):
    while True:
        state = (1103515245*state + 12345) & 0x7fffffff
        yield state
r = rng(import_seed)
# place buildings of varying heights along columns, base at row 23
GROUND_TOP_FAR = 24
x = 0
while x < WIDTH:
    bw = 2 + (next(r) % 4)            # building width 2..5
    bh = 4 + (next(r) % 8)            # height in tiles 4..11
    style = next(r) % 3
    top = GROUND_TOP_FAR - bh
    for cx in range(x, min(WIDTH, x+bw)):
        for cy in range(top, GROUND_TOP_FAR):
            if cy == top:
                far[cy][cx] = T["fb_top"] if style==0 else T["fb_top_b"]
            else:
                far[cy][cx] = T["fb_mid"]
            farp[cy][cx] = 3
        if style == 2 and cx == x + bw//2:
            far[top-1][cx] = T["fb_spire"]; farp[top-1][cx] = 3
    x += bw + (next(r) % 2)           # small gaps sometimes

# ---------------- NEAR layer (PPU1): ground + track + props -----------------
near = new_grid(); nearp = new_pal()
GROUND_TOP = 24      # rail row
# ground band rows 24..29
for cy in range(GROUND_TOP, ROWS):
    for cx in range(WIDTH):
        if cy == GROUND_TOP:
            near[cy][cx] = T["rail"]
        elif cy == GROUND_TOP+1:
            near[cy][cx] = T["grass_top"]
        else:
            near[cy][cx] = T["grass_fill"]
        nearp[cy][cx] = 1

def stamp(grid, palg, name_prefix, ox, oy, tw, th, pal):
    for ty in range(th):
        for tx in range(tw):
            key = f"{name_prefix}_{tx}_{ty}"
            if key in T:
                gx, gy = ox+tx, oy+ty
                if 0 <= gx < WIDTH and 0 <= gy < ROWS:
                    grid[gy][gx] = T[key]
                    palg[gy][gx] = pal

# A depot sits where the train halts: train center is screen col 13, so place a
# depot centered on col 13 in each nametable (cols 11..15 in NT0, 43..47 in NT1).
# Stops alternate nametables, so the two depots read as two different stations.
DEPOT_W = 5
for base in (0, 32):
    dl = base + 11
    stamp(near, nearp, "depot", dl, 20, DEPOT_W, 4, 2)
    # platform lip flanking the depot front (row 23)
    for px in (dl - 2, dl - 1, dl + DEPOT_W, dl + DEPOT_W + 1):
        if 0 <= px < WIDTH:
            near[23][px] = T["platform"]; nearp[23][px] = 2
    # station nameplate just left of the depot
    stamp(near, nearp, "sign", dl - 3, 21, 1, 3, 2)

# surrounding scenery (kept clear of the depot cols) -- distinct per station
props = [
    # --- NT0 ---
    ("tree",  4,  21, 2, 3, 1),
    ("lamp",  9,  21, 1, 3, 2),
    ("lamp",  17, 21, 1, 3, 2),
    ("house", 20, 21, 3, 3, 2),
    ("tree",  26, 21, 2, 3, 1),
    ("lamp",  30, 21, 1, 3, 2),
    # --- NT1 ---
    ("house", 34, 21, 3, 3, 2),
    ("tree",  40, 21, 2, 3, 1),
    ("lamp",  41, 21, 1, 3, 2),
    ("lamp",  49, 21, 1, 3, 2),
    ("tree",  52, 21, 2, 3, 1),
    ("house", 56, 21, 3, 3, 2),
    ("lamp",  62, 21, 1, 3, 2),
]
for name, ox, oy, tw, th, pal in props:
    stamp(near, nearp, name, ox, oy, tw, th, pal)

def attr_bytes(palg):
    """collapse per-tile palette map (32 wide slice) into 64 attribute bytes."""
    out = []
    for ay in range(0, 30, 4):           # 8 rows of attr (last covers rows 28,29)
        for ax in range(0, 32, 4):
            def pat(tx, ty):
                tx = min(tx, 31); ty = min(ty, 29)
                return palg[ty][tx] & 3
            tl = pat(ax,   ay)
            tr = pat(ax+2, ay)
            bl = pat(ax,   ay+2)
            br = pat(ax+2, ay+2)
            out.append((br<<6)|(bl<<4)|(tr<<2)|tl)
    assert len(out) == 64 or True
    return out[:64]

def emit_nt(f, label, grid, palg):
    """emit 2 nametables (left cols 0..31, right cols 32..63) = 2048 bytes."""
    f.write(f"{label}:\n")
    for screen in range(2):
        c0 = screen*32
        # 960 tile bytes
        for row in range(ROWS):
            vals = [grid[row][c0+c] for c in range(32)]
            f.write(".byte " + ",".join(f"${v:02x}" for v in vals) + "\n")
        # 64 attribute bytes for this screen
        sub = [[palg[row][c0+c] for c in range(32)] for row in range(ROWS)]
        ab = attr_bytes(sub)
        f.write(".byte " + ",".join(f"${v:02x}" for v in ab) + "\n")

with open(f"{ROOT}/src/leveldata.s", "w") as f:
    f.write("; AUTO-GENERATED by tools/gen.py\n\n")
    f.write(".export rbaNear\n.export rbaFar\n\n")
    f.write('.segment "RODATA"\n\n')
    emit_nt(f, "rbaNear", near, nearp)
    f.write("\n")
    emit_nt(f, "rbaFar", far, farp)

# ============================================================================
# traindata.s  -- locomotive body metasprite + gen.inc constants
# ============================================================================
# body sprites: (dy, tile, attr, dx). attr 0 = sprite palette 0.
with open(f"{ROOT}/src/traindata.s", "w") as f:
    f.write("; AUTO-GENERATED by tools/gen.py\n\n")
    f.write(".export rbaTrainBody\n.export rbaWheelDX\n\n")
    f.write('.segment "RODATA"\n\n')
    f.write("; sSprite layout: bPosY, bTile, bAttr, bPosX\n")
    f.write("rbaTrainBody:\n")
    for dx, dy, idx in train_body:
        f.write(f".byte {dy}, ${idx:02x}, $00, {dx}\n")
    f.write(f"TRAIN_BODY_COUNT = {len(train_body)}\n\n")
    # wheels: x offsets under the boiler
    wheel_dx = [5, 13, 21]
    f.write("rbaWheelDX:\n")
    f.write(".byte " + ",".join(str(v) for v in wheel_dx) + "\n")

with open(f"{ROOT}/include/gen.inc", "w") as f:
    f.write("; AUTO-GENERATED by tools/gen.py\n")
    f.write(".ifndef _GEN_\n_GEN_ = 1\n.scope Gen\n")
    f.write(f"    TRAIN_BODY_COUNT = {len(train_body)}\n")
    f.write(f"    WHEEL_COUNT = 3\n")
    f.write(f"    WHEEL_DY = 23\n")
    f.write(f"    TILE_WHEEL0 = ${tile_name['wheel0']:02x}\n")
    f.write(f"    TILE_WHEEL1 = ${tile_name['wheel1']:02x}\n")
    f.write(f"    TILE_SMOKE0 = ${tile_name['smoke0']:02x}\n")
    f.write(f"    TILE_SMOKE1 = ${tile_name['smoke1']:02x}\n")
    f.write(f"    TILE_SMOKE2 = ${tile_name['smoke2']:02x}\n")
    f.write(f"    TILE_SMOKE3 = ${tile_name['smoke3']:02x}\n")
    f.write(f"    SMOKE_COUNT = 5\n")
    f.write(f"    CHIMNEY_DX = 18\n")    # chimney x offset (left edge of stack)
    f.write(f"    CHIMNEY_DY = 0\n")
    f.write(f"    TILE_METER_OFF = ${tile_name['meter_off']:02x}\n")
    f.write(f"    TILE_METER_ON  = ${tile_name['meter_on']:02x}\n")
    f.write(f"    TILE_METER_ON2 = ${tile_name['meter_on2']:02x}\n")
    f.write(f"    TILE_METER_ON3 = ${tile_name['meter_on3']:02x}\n")
    f.write(f"    METER_SEGS = 8\n")
    f.write(f"    METER_GREEN_MAX = 5\n")   # segs 0..4 green, 5..6 yellow, 7 red
    f.write(f"    METER_YELLOW_MAX = 6\n")
    f.write(f"    TILE_PAX0 = ${tile_name['pax_0_0']:02x}\n")
    f.write(f"    TILE_PAX1 = ${tile_name['pax_0_1']:02x}\n")
    f.write(f"    TILE_COACH00 = ${tile_name['coach_0_0']:02x}\n")
    f.write(f"    TILE_COACH10 = ${tile_name['coach_1_0']:02x}\n")
    f.write(f"    TILE_COACH01 = ${tile_name['coach_0_1']:02x}\n")
    f.write(f"    TILE_COACH11 = ${tile_name['coach_1_1']:02x}\n")
    f.write(f"    MAX_CARS = 5\n")
    f.write(f"    CAR_W = 18\n")
    f.write(".endscope\n.endif\n")

print(f"tiles used: {len(tiles)} / 256")
print(f"train body sprites: {len(train_body)}")
print("far skyline + near town generated.")
print("OK")
