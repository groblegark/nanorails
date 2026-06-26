
.ifndef _INPUT_
    _INPUT_ = 1

    .scope Input

        .importzp rzbJoypad1

        .import read_joypad1

        ; joypad addresses
        JOYPAD1 = $4016
        JOYPAD2 = $4017

        ; joypad bit masks
        JOYPAD_A      = %10000000
        JOYPAD_B      = %01000000
        JOYPAD_SELECT = %00100000
        JOYPAD_START  = %00010000
        JOYPAD_UP     = %00001000
        JOYPAD_DOWN   = %00000100
        JOYPAD_LEFT   = %00000010
        JOYPAD_RIGHT  = %00000001

    .endscope

.endif
