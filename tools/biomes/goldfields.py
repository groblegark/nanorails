# Goldfields -- rural farmland: rippling golden wheat, a big red barn, a tall
# windmill, round hay bales and fences, with low rolling green hills + a dotting
# of distant red-roofed farmhouses on the horizon. Bright day sky.
#
# Palette plan (c0 == sky == 0x22 day blue):
#   pal1 ground : 1=pale wheat,  2=furrow brown, 3=olive stalk
#   pal2 props  : 1=barn red,    2=dark wood,    3=white/cream trim
#   pal3 far    : 1=hill green,  2=hill shade,   3=red farmhouse roof

# ---- ground: wheat field with wind-ripple + furrow rows ---------------------
define_tile("farm_field_top", [   # heads of grain catch the light, green tips
    "00000000",
    "31013103",   # seed heads + a stray green blade
    "11311311",
    "11111111",
    "21121121",   # furrow shadow specks
    "11111111",
    "13111311",
    "11111111",
])
define_tile("farm_field", [       # body: gentle diagonal ripple of the crop
    "11111121",
    "11111211",
    "11112111",
    "11121111",
    "11211111",
    "12111111",
    "21111111",
    "11111112",
])

# ---- red barn (24x24 -> 3x3 tiles): gambrel roof, hay loft + big doors -------
barn = Canvas(24, 24)
barn.rect(2, 11, 22, 24, 1)                 # red walls
for y in range(0, 5):                       # gambrel: shallow upper pitch
    half = 7 + y
    barn.rect(12-half, y, 12+half, y+1, 2)
for y in range(5, 11):                       # steep lower pitch
    half = 11 + (y-5)//3
    barn.rect(12-half, y, 12+half, y+1, 2)
barn.rect(0, 10, 24, 12, 2)                 # eave shadow band
barn.rect(0, 10, 24, 11, 3)                 # white eave trim
barn.rect(9, 4, 15, 9, 3); barn.rect(10, 5, 14, 9, 2)   # hay-loft door
barn.rect(7, 14, 17, 24, 3)                 # white double doors
barn.vline(12, 14, 24, 2)                    # door split
# painted X braces on the doors
for k in range(7):
    barn.pset(8+k, 15+k, 2);  barn.pset(16-k, 15+k, 2)
barn.vline(2, 11, 24, 3); barn.vline(21, 11, 24, 3)     # white corner boards
for tx, ty, rows, empty in barn.slice_tiles():
    if not empty:
        define_tile(f"farm_barn_{tx//8}_{ty//8}", rows)

# ---- windmill (8x24 -> 1x3): slim white tower + 4 sails ----------------------
mill = Canvas(8, 24)
mill.rect(2, 9, 6, 24, 3)                   # white tower
mill.vline(2, 9, 24, 2); mill.vline(5, 9, 24, 2)        # tower edges
mill.rect(2, 15, 6, 16, 2)                  # mid band
mill.rect(3, 20, 5, 24, 2)                  # door
mill.rect(3, 6, 5, 9, 2)                    # hub
mill.vline(4, 0, 8, 2); mill.hline(0, 8, 4, 2)          # sail spars (cross)
mill.rect(3, 0, 6, 2, 3)                    # top sail blade
mill.rect(5, 3, 8, 5, 3)                    # right blade
mill.rect(0, 4, 3, 6, 3)                    # left blade
for tx, ty, rows, empty in mill.slice_tiles():
    if not empty:
        define_tile(f"farm_mill_{tx//8}_{ty//8}", rows)

# ---- round hay bale (8x8): golden roll with binding band ---------------------
define_tile("farm_hay", [
    "00000000",
    "00111100",
    "01311310",
    "13131311",
    "11313131",
    "13131311",
    "01311310",
    "00111100",
])

# ---- far rolling-hill cap (rounded green crown over a green body) ------------
define_tile("farm_hill", [
    "00000000",
    "00000000",
    "00011110",
    "00111111",
    "01111111",
    "11111111",
    "11211211",   # subtle shade dapple
    "11111111",
])
# ---- tiny distant farmhouse (red roof / pale wall) ---------------------------
define_tile("farm_house", [
    "00000000",
    "00033000",
    "00333300",
    "03333330",
    "03311330",
    "03131330",
    "03311330",
    "00000000",
])


def build_goldfields(near, nearp, far, farp, rng):
    fill_ground(near, nearp, 1, rail="rail",
                top="farm_field_top", fill="farm_field")
    place_depots(near, nearp, 2)
    scatter(near, nearp, [
        ("farm_barn", 3, 3, 2),
        ("farm_hay",  1, 1, 2),
        ("farm_mill", 1, 3, 2),
        ("fence",     1, 1, 2),
        ("farm_barn", 3, 3, 2),
        ("farm_hay",  1, 1, 2),
    ], rng)
    # far: a low band of rolling hills (1-2 tiles tall) along the horizon
    x = 0
    while x < WIDTH:
        bw = 3 + (rng() % 5)
        h2 = (rng() % 3 == 0)              # occasional taller swell
        topr = 22 if h2 else 23
        for cx in range(x, min(WIDTH, x + bw)):
            far[topr][cx] = T["farm_hill"]; farp[topr][cx] = 3
            if h2:
                far[23][cx] = T["grass_fill"]; farp[23][cx] = 3
        # a farmhouse perched on some hills
        if rng() % 3 == 0 and x + 1 < WIDTH:
            far[topr - 1][x + 1] = T["farm_house"]; farp[topr - 1][x + 1] = 3
        x += bw


add_biome("Goldfields", 0x22,
          [[0x22, 0x30, 0x10, 0x00],   # pal0 ui/sky detail
           [0x22, 0x38, 0x17, 0x28],   # pal1 ground: wheat / furrow / stalk
           [0x22, 0x16, 0x07, 0x30],   # pal2 props: barn-red / wood / white
           [0x22, 0x2A, 0x1A, 0x16]],  # pal3 far:   hill / shade / red roof
          build_goldfields)
