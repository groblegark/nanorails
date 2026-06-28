# Tidewater -- a sunny coastal seaside biome.
#   ground : pale beach sand with shell flecks
#   props  : palm trees (tall, leaning fronds), a striped beach umbrella
#   far    : teal/blue ocean with a wave-cap horizon + a distant sailboat
#   sky    : bright day blue
#
# Palette plan (c0 must equal sky 0x22):
#   pal0 ground : 1=beach sand, 2=wet-sand shadow, 3=shell/pale highlight
#   pal1 props  : 1=palm frond green, 2=trunk brown, 3=umbrella red/bloom
#   pal2 depot  : 1=adobe/board wall, 2=roof, 3=trim  (place_depots)
#   pal3 far    : 1=ocean teal, 2=deep blue, 3=white wave-cap / sail

# ---- ground tiles ----------------------------------------------------------
define_tile("sea_sand_top", [
    "11111111",
    "11111111",
    "11311111",   # shell fleck
    "11111111",
    "11111131",
    "11111111",
    "13111111",
    "11111111",
])
define_tile("sea_sand", [
    "11111111",
    "11111111",
    "11111111",
    "12111111",   # faint damp patch
    "11111111",
    "11111121",
    "11111111",
    "11111111",
])

# ---- palm tree : 2 wide x 3 tall -------------------------------------------
palm = Canvas(16, 24)
# leaning trunk (brown), curving up-right
palm.rect(5, 22, 8, 24, 2)
palm.rect(6, 18, 9, 22, 2)
palm.rect(7, 14, 10, 18, 2)
palm.rect(8, 9, 11, 14, 2)
palm.vline(8, 9, 22, 1)            # light side of trunk
# coconuts at the crown
palm.pset(7, 9, 3); palm.pset(11, 9, 3)
# drooping fronds (green) radiating from the crown ~ (9,8)
palm.rect(1, 4, 9, 6, 1)           # left frond
palm.rect(0, 6, 5, 8, 1)
palm.rect(9, 3, 16, 5, 1)          # right frond
palm.rect(11, 5, 16, 8, 1)
palm.rect(5, 0, 12, 3, 1)          # top frond
palm.rect(2, 8, 7, 10, 1)          # lower-left droop
palm.rect(10, 8, 15, 11, 1)        # lower-right droop
# dark green shading on fronds
palm.rect(5, 1, 11, 2, 2)
palm.pset(2, 5, 2); palm.pset(13, 4, 2); palm.pset(3, 9, 2); palm.pset(12, 9, 2)
for tx, ty, rows, empty in palm.slice_tiles():
    define_tile(f"sea_palm_{tx//8}_{ty//8}", rows)

# ---- beach umbrella : 2 wide x 2 tall --------------------------------------
umb = Canvas(16, 16)
# canopy dome (red/white stripes)
umb.rect(1, 4, 15, 8, 3)
umb.rect(3, 2, 13, 4, 3)
umb.rect(6, 1, 10, 2, 3)
umb.vline(4, 4, 8, 1); umb.vline(7, 2, 8, 1)    # white stripe gaps
umb.vline(10, 2, 8, 1); umb.vline(12, 4, 8, 1)
umb.rect(1, 7, 15, 8, 2)           # rim shadow
# pole + base
umb.vline(8, 8, 16, 2)
umb.rect(6, 14, 11, 16, 1)         # sand mound at base
for tx, ty, rows, empty in umb.slice_tiles():
    define_tile(f"sea_umbrella_{tx//8}_{ty//8}", rows)

# ---- far ocean tiles -------------------------------------------------------
define_tile("sea_wave", [          # horizon row: white caps on teal
    "00000000",
    "00100100",
    "01310310",   # foam crests
    "13111311",
    "11111111",
    "11211121",
    "11111111",
    "12111211",
])
define_tile("sea_water", [
    "11111111",
    "11111111",
    "12111121",   # gentle swell shading
    "11111111",
    "11111111",
    "11311111",   # glint
    "11111111",
    "12111111",
])
# distant sailboat (single tile) : white sail + hull on the water
define_tile("sea_boat", [
    "00033000",   # sail top
    "00033100",
    "00333100",
    "03333100",
    "03333100",
    "00000100",   # mast base
    "00222000",   # hull
    "12222221",
])


def build_tidewater(near, nearp, far, farp, rng):
    fill_ground(near, nearp, 0, top="sea_sand_top", fill="sea_sand")
    place_depots(near, nearp, 2)
    scatter(near, nearp, [
        ("sea_palm",     2, 3, 1),
        ("sea_umbrella", 2, 2, 1),
        ("sea_palm",     2, 3, 1),
        ("sea_palm",     2, 3, 1),
    ], rng)
    # flat ocean band: a wave-cap crest line on top of a deep-water body.
    horizon = 16                      # ocean meets sky high up
    crest = GROUND_TOP - 1            # foam line nearest the beach (row 23)
    for cx in range(WIDTH):
        for cy in range(horizon, GROUND_TOP):
            far[cy][cx] = T["sea_water"]
            farp[cy][cx] = 3
        # foam crest both at the far horizon and at the near shoreline
        far[horizon][cx] = T["sea_wave"]
        far[crest][cx] = T["sea_wave"]
        farp[horizon][cx] = 3
        farp[crest][cx] = 3
    # a few distant sailboats riding the swell
    for bx in (8 + rng() % 5, 24 + rng() % 5, 42 + rng() % 5):
        if 0 <= bx < WIDTH:
            far[horizon + 2 + rng() % 3][bx] = T["sea_boat"]
            farp[horizon + 2][bx] = 3


add_biome("Tidewater", 0x22, [
    [0x22, 0x37, 0x27, 0x30],   # 0 ground : warm sand, tan shadow, white shell
    [0x22, 0x1A, 0x17, 0x16],   # 1 props  : palm green, trunk brown, umbrella red
    [0x22, 0x16, 0x07, 0x30],   # 2 depot  : weathered red, brown, white trim
    [0x22, 0x2C, 0x11, 0x30],   # 3 far    : ocean teal, deep blue, white cap/sail
], build_tidewater)
