# Emberwood -- autumn forest: a carpet of fallen leaves, broad maples with
# fiery red/orange/gold canopies on brown trunks, low autumn shrubs, and a warm
# banked treeline of fall colour along the horizon. Soft pale-orange sky.
#
# Palette plan (c0 == sky == 0x27 pale orange):
#   pal1 ground : 1=tan leaf litter, 2=dark earth,  3=red fallen leaf
#   pal2 trees  : 1=red canopy,      2=mid brown,    3=pale-gold highlight
#   pal3 far    : 1=orange treeline, 2=brown shade,  3=red crown

# ---- ground: leaf-litter carpet ---------------------------------------------
define_tile("fall_litter_top", [   # surface w/ scattered curled red leaves
    "00000000",
    "30100301",
    "11131113",
    "11111111",
    "13111311",
    "11211121",
    "11131113",
    "11111111",
])
define_tile("fall_litter", [       # deeper litter: mixed reds + bare earth
    "11131113",
    "11111111",
    "31113112",
    "11211121",
    "11131113",
    "11111111",
    "21113111",
    "11211121",
])

# ---- broad autumn maple (24x24 -> 3x3): big rounded fiery crown, brown trunk -
maple = Canvas(24, 24)
maple.rect(10, 16, 14, 24, 2)               # trunk (mid brown)
maple.pset(9, 23, 2); maple.pset(14, 23, 2) # root flare
maple.vline(11, 16, 24, 1)                   # bark highlight streak
maple.rect(2, 1, 22, 17, 1)                 # full red canopy block
for (x, y) in [(2,1),(3,1),(4,1),(2,2),(3,2),(19,1),(20,1),(21,1),(20,2),(21,2),
               (2,16),(3,16),(20,16),(21,16),(1,9),(22,9),(1,8),(22,8),(2,15),(21,15)]:
    maple.pset(x, y, 0)                      # round the crown
# generous pale-gold sunlit clumps (3) — these make it read as autumn fire
maple.rect(5, 3, 10, 7, 3); maple.rect(13, 5, 19, 9, 3)
maple.rect(7, 11, 13, 15, 3); maple.rect(3, 10, 6, 13, 3)
maple.rect(16, 12, 20, 16, 3)
# a few deep-shade pockets (2) for depth
maple.rect(10, 7, 13, 10, 2); maple.rect(5, 13, 7, 15, 2)
maple.pset(15,3,3); maple.pset(4,5,3); maple.pset(18,14,3)
for tx, ty, rows, empty in maple.slice_tiles():
    if not empty:
        define_tile(f"fall_tree_{tx//8}_{ty//8}", rows)

# ---- low autumn shrub (16x16 -> 2x2): rounded gold-and-red bush --------------
bush = Canvas(16, 16)
bush.rect(1, 4, 15, 16, 1)                  # red mound
for (x, y) in [(1,4),(2,4),(1,5),(13,4),(14,4),(14,5),(1,15),(14,15)]:
    bush.pset(x, y, 0)
bush.rect(3, 6, 7, 10, 3); bush.rect(9, 7, 13, 11, 3)   # gold highlights
bush.rect(6, 11, 10, 14, 3)
bush.pset(5, 5, 3); bush.pset(11, 6, 3)
bush.rect(7, 8, 9, 11, 2)                   # tiny shade pocket
for tx, ty, rows, empty in bush.slice_tiles():
    if not empty:
        define_tile(f"fall_bush_{tx//8}_{ty//8}", rows)

# ---- far treeline crown (rounded fall foliage dome) -------------------------
define_tile("fall_far_crown", [    # fiery dome top, dappled red/orange
    "00011000",
    "00111100",
    "01311310",
    "11131111",
    "31111131",
    "11311131",
    "11111111",
    "11211211",
])


def build_emberwood(near, nearp, far, farp, rng):
    fill_ground(near, nearp, 1, rail="rail",
                top="fall_litter_top", fill="fall_litter")
    place_depots(near, nearp, 2)
    scatter(near, nearp, [
        ("fall_tree", 3, 3, 2),
        ("fall_bush", 2, 2, 2),
        ("fall_tree", 3, 3, 2),
        ("fall_bush", 2, 2, 2),
    ], rng)
    # far: a banked warm treeline (2-3 tiles tall) of rounded crowns
    x = 0
    while x < WIDTH:
        bw = 2 + (rng() % 4)
        h = 2 + (rng() % 2)                  # 2-3 tiles tall
        top = 24 - h
        for cx in range(x, min(WIDTH, x + bw)):
            for cy in range(top, 24):
                far[cy][cx] = T["fall_far_crown"] if cy == top else T["fall_litter"]
                farp[cy][cx] = 3
        x += bw


# Crisp pale-cyan autumn sky (0x2C) so the warm reds/golds pop instead of
# blending into a warm backdrop.
add_biome("Emberwood", 0x2C,
          [[0x2C, 0x30, 0x10, 0x00],   # pal0 ui/sky detail
           [0x2C, 0x37, 0x07, 0x16],   # pal1 ground: tan litter / earth / red
           [0x2C, 0x16, 0x17, 0x38],   # pal2 trees:  red / brown / pale-gold
           [0x2C, 0x27, 0x07, 0x16]],  # pal3 far:    orange / brown / red
          build_emberwood)
