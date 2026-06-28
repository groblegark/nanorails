# Highpass -- a high rocky mountain pass at dusk, snow-capped peaks behind.
# Palette plan (c0 == sky 0x12 dusk):
#   pal0 misc    : [sky, slate, white, dark]
#   pal1 ground  : [sky, rock-gray, dark-slate, dusty-brown]   1=rock 2=shadow 3=scree
#   pal2 props   : [sky, evergreen, slate-rock, snow/brown]    (boulders + depot)
#   pal3 far     : [sky, slate-blue, white-snow, deep-slate]   1=slope 2=cap 3=shade
#
# New tiles: hp_rail, hp_rtop, hp_rfill (ground 3) + hp_bldr 2x2 (4)
#            + mtn_peak, mtn_slope, mtn_peakb (far 3) = 10 new tiles.

# ---- ground: broken rock & scree over the embankment -----------------------
define_tile("hp_rail", [    # steel rail over gravel ballast
    "22222222",   # rail head (dark slate)
    "00000000",
    "33033033",   # ties
    "33033033",
    "11111111",   # gravel
    "12111211",
    "11211111",
    "11111111",
])
define_tile("hp_rtop", [    # rocky surface with cracks & pebbles
    "00000000",
    "11211311",
    "12111121",
    "11111111",
    "11311211",
    "11111111",
    "12111131",
    "11111111",
])
define_tile("hp_rfill", [   # bedrock with strata shading
    "11111111",
    "21111112",
    "11111111",
    "11211131",
    "11111111",
    "31111112",
    "11111111",
    "11311211",
])

# ---- near boulder cluster: 16x16, mossy-topped granite ---------------------
# 1=rock-gray? props use pal2: 1=evergreen, 2=slate-rock, 3=snow/brown.
# Use 2=rock body, 1=mossy green highlight, 3=light brown facet.
bd = Canvas(16, 16)
bd.rect(2, 6, 14, 16, 2)                 # big boulder
bd.rect(0, 9, 6, 16, 2)                  # smaller one front-left
bd.rect(11, 10, 16, 16, 2)              # chip front-right
# round the tops
for (x, y) in [(2,6),(13,6),(0,9),(5,9),(11,10),(15,10)]:
    bd.pset(x, y, 0)
bd.rect(4, 7, 11, 9, 3)                   # lit facet (lighter)
bd.pset(2, 12, 3); bd.pset(9, 13, 3)
bd.rect(3, 6, 9, 7, 1); bd.pset(7,6,1)    # moss on the crown
bd.pset(1, 9, 1); bd.pset(12, 10, 1)
for tx, ty, rows, empty in bd.slice_tiles():
    if not empty:
        define_tile(f"hp_bldr_{tx//8}_{ty//8}", rows)

# ---- far layer: big triangular snow-capped peaks ---------------------------
# Built from edge tiles so the silhouette tapers to a point.
define_tile("mtn_apex", [   # snow summit point
    "00011000",
    "00111100",
    "00122100",   # 2=cap white, with a touch of rock shade
    "01122110",
    "01222210",
    "11222111",
    "11122111",
    "11112111",
])
define_tile("mtn_le", [     # left slope edge (rock, lit), transparent upper-left
    "00000111",
    "00001111",
    "00011311",
    "00111111",
    "01111111",
    "01113111",
    "11111111",
    "11131111",
])
define_tile("mtn_re", [     # right slope edge, transparent upper-right
    "11100000",
    "11110000",
    "11311000",
    "11111100",
    "11111110",
    "11131110",
    "11111110",
    "11111310",
])
define_tile("mtn_slope", [  # mountain body: rock with snow streaks & gullies
    "11111111",
    "13111211",
    "11111111",
    "11211131",
    "11111111",
    "31111211",
    "11131111",
    "11111111",
])
define_tile("mtn_snow", [   # upper body still under snow (2) with rock showing
    "22122212",
    "21222122",
    "12221221",
    "22122212",
    "11221121",
    "21121211",
    "11211111",
    "11111111",
])


def _mountain(far, farp, rng, base, pal, minh, maxh):
    """Paint a range of triangular peaks. Each peak: apex tile at top, then
    widening rows of slope flanked by edge tiles, snow on the upper third."""
    x = 0
    while x < WIDTH:
        h = minh + (rng() % max(1, maxh - minh))     # height in tiles
        top = base - h
        # peak grows ~1 col wider per row down from the apex
        apex = x + 1 + (rng() % 2)
        for i in range(h):
            cy = top + i
            if cy < 0:
                continue
            half = (i + 1) // 2
            l = apex - half
            r = apex + half
            snow = i < max(2, h // 3)                  # snowy near the top
            for cx in range(l, r + 1):
                if not (0 <= cx < WIDTH):
                    continue
                if i == 0:
                    t = "mtn_apex"
                elif cx == l:
                    t = "mtn_le"
                elif cx == r:
                    t = "mtn_re"
                else:
                    t = "mtn_snow" if snow else "mtn_slope"
                far[cy][cx] = T[t]; farp[cy][cx] = pal
        x = r + 1 + (rng() % 2)


def build_highpass(near, nearp, far, farp, rng):
    fill_ground(near, nearp, 1, rail="hp_rail", top="hp_rtop", fill="hp_rfill")
    place_depots(near, nearp, 2)
    # hardy evergreens clinging to the pass + scattered boulders
    scatter(near, nearp, [
        ("tree",    2, 3, 2),
        ("hp_bldr", 2, 2, 2),
        ("tree",    2, 3, 2),
        ("hp_bldr", 2, 2, 2),
    ], rng)
    # far: hazy back range (lower), then a bold front range of taller peaks
    _mountain(far, farp, rng, base=24, pal=3, minh=4, maxh=7)
    _mountain(far, farp, rng, base=24, pal=3, minh=7, maxh=12)


add_biome("Highpass", 0x12,
          [[0x12, 0x00, 0x30, 0x0F],   # pal0
           [0x12, 0x00, 0x2D, 0x08],   # pal1 ground: rock-gray, dark-slate, scree-brown
           [0x12, 0x18, 0x00, 0x30],   # pal2 props: evergreen, slate-rock, snow/brown
           [0x12, 0x2D, 0x30, 0x0F]],  # pal3 far: slate-blue, white, deep slate
          build_highpass)
