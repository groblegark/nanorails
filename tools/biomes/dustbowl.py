# Dustbowl -- a hot desert biome.
#   ground : sandy tan with scattered pebbles
#   props  : tall saguaro cactus, sun-bleached rock + cattle skull
#   far    : rolling sand dunes in a hazy heat-tan
#   sky    : sunset orange
#
# Palette plan (c0 must equal sky 0x17):
#   pal0 ground : 1=sand tan, 2=shadow brown, 3=dark brown pebble
#   pal1 cactus : 1=cactus green, 2=dark green shade, 3=yellow flower/bloom
#   pal2 depot  : 1=adobe wall, 2=brown roof/outline, 3=cream trim  (place_depots)
#   pal3 far    : 1=dune tan, 2=hazy shadow, 3=warm highlight

# ---- ground tiles ----------------------------------------------------------
define_tile("dust_sand_top", [
    "11111111",
    "11211121",   # faint ripple shadows
    "11111111",
    "11111311",   # stray pebble
    "11111111",
    "13111111",
    "11111111",
    "11112111",
])
define_tile("dust_sand", [
    "11111111",
    "11111111",
    "11211111",
    "11111111",
    "11111311",
    "11111111",
    "11111121",
    "11111111",
])

# ---- saguaro cactus : 2 wide x 3 tall -------------------------------------
cac = Canvas(16, 24)
cac.rect(6, 2, 10, 24, 1)          # central trunk
cac.rect(2, 9, 6, 12, 1)           # left arm horizontal
cac.rect(2, 6, 5, 12, 1)           # left arm rising
cac.rect(10, 12, 14, 15, 1)        # right arm horizontal
cac.rect(11, 8, 14, 15, 1)         # right arm rising
# vertical pleat shading (dark green)
cac.vline(7, 3, 24, 2)
cac.vline(3, 7, 11, 2)
cac.vline(12, 9, 14, 2)
# yellow blossoms at the tips
cac.rect(7, 1, 9, 3, 3)
cac.rect(2, 5, 5, 7, 3)
cac.rect(11, 7, 14, 9, 3)
for tx, ty, rows, empty in cac.slice_tiles():
    define_tile(f"dust_cactus_{tx//8}_{ty//8}", rows)

# ---- sun-bleached rock + cattle skull : 2 wide x 2 tall --------------------
rk = Canvas(16, 16)
# boulder (right) -- cream/tan with brown crack shading
rk.rect(9, 6, 16, 16, 1)
rk.rect(9, 5, 14, 7, 1)
rk.vline(12, 7, 16, 2)             # crack
rk.rect(10, 12, 16, 16, 2)         # base shadow
# cattle skull (left) -- pale cream with horns
rk.rect(2, 9, 8, 15, 3)            # cranium (bright cream)
rk.rect(0, 8, 3, 10, 3)            # left horn
rk.rect(7, 8, 10, 10, 3)           # right horn
rk.pset(3, 12, 2); rk.pset(6, 12, 2)   # eye sockets
rk.rect(4, 14, 6, 16, 2)           # snout shadow
for tx, ty, rows, empty in rk.slice_tiles():
    define_tile(f"dust_rock_{tx//8}_{ty//8}", rows)

# ---- far dune tiles --------------------------------------------------------
define_tile("dust_dune_top", [
    "00000000",
    "00000011",
    "00001111",
    "00111111",
    "01111113",   # warm highlight on crest
    "11111111",
    "11111111",
    "11211111",
])
define_tile("dust_dune", [
    "11111111",
    "11111111",
    "11111112",
    "11111111",
    "12111111",
    "11111111",
    "11111121",
    "11111111",
])


def build_dustbowl(near, nearp, far, farp, rng):
    fill_ground(near, nearp, 0, top="dust_sand_top", fill="dust_sand")
    place_depots(near, nearp, 2)
    scatter(near, nearp, [
        ("dust_cactus", 2, 3, 1),
        ("dust_rock",   2, 2, 1),
        ("dust_cactus", 2, 3, 1),
        ("dust_rock",   2, 2, 1),
    ], rng)
    # rolling dunes in hazy tan: a low far band plus a slightly taller near band
    far_silhouette(far, farp, rng, 3, ["dust_dune_top"], "dust_dune",
                   base=24, minh=2, maxh=5)
    far_silhouette(far, farp, rng, 3, ["dust_dune_top"], "dust_dune",
                   base=24, minh=4, maxh=8)


add_biome("Dustbowl", 0x27, [
    [0x27, 0x17, 0x07, 0x37],   # 0 ground : tan sand, mid brown, dark brown, hot cream
    [0x27, 0x1A, 0x09, 0x28],   # 1 cactus : green, dark green, yellow bloom
    [0x27, 0x16, 0x07, 0x36],   # 2 depot  : adobe red, brown, pink-cream trim
    [0x27, 0x17, 0x08, 0x37],   # 3 far    : dune tan, hazy brown shadow, hot crest
], build_dustbowl)
