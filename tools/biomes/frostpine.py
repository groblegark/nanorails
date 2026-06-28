# Frostpine -- a hushed snowy conifer forest.
# Palette plan (c0 == sky 0x2C pale cyan):
#   pal0 misc      : [sky, white, lightblue, steel]
#   pal1 ground    : [sky, snow-white, ice-blue, blue-shadow]   1=snow 2=ice 3=shadow
#   pal2 props     : [sky, dark-green, snow-white, trunk-brown] 1=needles 2=snowcap 3=trunk
#   pal3 far       : [sky, frost-blue, white, deep-teal]        1=tree 2=cap 3=shade
#
# New tiles: fp_srail, fp_stop, fp_sfill (ground 3) + snow pine 2x3 (5 used)
#            + far conifer fp_far + snow hill fp_fhill (2) = 10 new tiles.

# ---- ground: fresh snow over the embankment --------------------------------
define_tile("fp_srail", [   # rail buried in snow: steel head, ties, snow ballast
    "11111111",   # snow lip
    "00000000",
    "33033033",   # ties (use 3=shadow under rail)
    "33033033",
    "11111111",   # packed snow
    "12111121",
    "11111111",
    "11111111",
])
define_tile("fp_stop", [    # snow surface with sparkle dimples
    "00000000",
    "11211211",
    "11111111",
    "11111111",
    "12111121",
    "11111111",
    "11111111",
    "11211121",
])
define_tile("fp_sfill", [   # packed snow with faint blue drift shading
    "11111111",
    "11111121",
    "11111111",
    "12111111",
    "11111111",
    "11111211",
    "11111111",
    "13111131",   # occasional cold shadow speckle
])

# ---- snow-laden pine: 16x24, sits on the snow -------------------------------
# 2=snow cap, 1=dark green needles, 3=trunk brown
sp = Canvas(16, 24)
sp.rect(7, 19, 9, 24, 3)                      # trunk
# three needle tiers widening downward
def tier(cx, top, half_top, half_bot, h):
    for i in range(h):
        half = half_top + (half_bot - half_top) * i // max(1, h - 1)
        sp.rect(cx - half, top + i, cx + half, top + i + 1, 1)
tier(8, 2, 1, 4, 5)      # top tier
tier(8, 7, 2, 6, 6)      # mid tier
tier(8, 13, 3, 7, 6)     # bottom tier
# snow caps sitting on each tier's left/top shoulders (2=white)
sp.rect(5, 2, 11, 4, 2); sp.pset(8,2,2); sp.pset(7,3,2); sp.pset(9,3,2)
sp.rect(4, 7, 9, 9, 2)
sp.rect(3, 13, 8, 15, 2)
sp.rect(10, 14, 13, 15, 2)
# a couple needle shadows for depth
sp.pset(11,11,3); sp.pset(12,17,3); sp.pset(4,17,3)
for tx, ty, rows, empty in sp.slice_tiles():
    if not empty:
        define_tile(f"fp_pine_{tx//8}_{ty//8}", rows)

# ---- far layer: snow-capped conifer & rounded white drift hill -------------
define_tile("fp_far", [     # distant frosted conifer: green body, white crown
    "00022000",             # 1=pine green, 2=white cap (no index3 -> shared pal)
    "00222200",
    "01122110",
    "01222210",
    "11211211",
    "01222210",
    "11111111",
    "00121200",
])
# rounded snow-drift hill pieces: a left brow, crown, and right brow so the
# silhouette curves instead of standing in flat columns.
# drift pieces share pal3 with the trees: 2=white snow, 3=frost-blue shade.
define_tile("fp_hbrowl", [  # left shoulder of a drift (rises L->R)
    "00000000",
    "00000000",
    "00000022",
    "00002222",
    "00222222",
    "02222223",   # 3=blue underside shade
    "22222233",
    "22233333",
])
define_tile("fp_hcrown", [  # rounded crown / body fill
    "22222222",
    "22222222",
    "23222232",
    "22322322",
    "33222333",
    "33333333",
    "33333333",
    "33333333",
])
define_tile("fp_hbrowr", [  # right shoulder (falls L->R)
    "00000000",
    "00000000",
    "22000000",
    "22220000",
    "22222200",
    "32222220",
    "33222222",
    "33333222",
])


def _drifts(far, farp, rng, pal, base):
    """Low rolling snow drifts: brow / crown / brow groups along the horizon."""
    x = 0
    while x < WIDTH:
        w = 3 + (rng() % 4)
        h = 2 + (rng() % 2)
        top = base - h
        for i, cx in enumerate(range(x, min(WIDTH, x + w))):
            if cx == x:
                edge = "fp_hbrowl"
            elif cx == x + w - 1:
                edge = "fp_hbrowr"
            else:
                edge = None
            for cy in range(top, base):
                if cy < 0:
                    continue
                t = edge if (edge and cy == top) else "fp_hcrown"
                far[cy][cx] = T[t]; farp[cy][cx] = pal
        x += w + (rng() % 2)


def build_frostpine(near, nearp, far, farp, rng):
    fill_ground(near, nearp, 1, rail="fp_srail", top="fp_stop", fill="fp_sfill")
    place_depots(near, nearp, 2)
    # dense snowy pines with the rare bare tree for variety
    scatter(near, nearp, [
        ("fp_pine", 2, 3, 2),
        ("fp_pine", 2, 3, 2),
        ("fp_pine", 2, 3, 2),
        ("tree",    2, 3, 2),
    ], rng)
    # far (all pal3): low rolling snow drifts topped by a frosted treeline
    _drifts(far, farp, rng, 3, base=24)
    # dense single-tile conifers marching along the drift crest, two depths
    for cx in range(WIDTH):
        if rng() % 3:                              # ~2/3 of columns: front tree
            far[22][cx] = T["fp_far"]; farp[22][cx] = 3
        if rng() % 2 == 0:                         # ~1/2: a taller back tree
            far[21][cx] = T["fp_far"]; farp[21][cx] = 3


add_biome("Frostpine", 0x2C,
          [[0x2C, 0x30, 0x21, 0x0F],   # pal0 (unused-ish)
           [0x2C, 0x30, 0x21, 0x11],   # pal1 ground: white, ice-blue, blue-shadow
           [0x2C, 0x09, 0x30, 0x07],   # pal2 props: dark green, snow-white, brown
           [0x2C, 0x1A, 0x30, 0x21]],  # pal3 far: pine-green, white-cap, frost-blue
          build_frostpine)
