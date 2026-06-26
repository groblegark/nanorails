
; definitions for the picture processing unit (PPU).

.ifndef _PPU_
    _PPU_ = 1

    .scope Ppu

        .importzp rzbMask
        .importzp rzbCtrl
        .importzp zbCtrl

        .importzp zbScrollX
        .importzp zbScrollY

        .import aOamBuffer


        .importzp rzbDualPpu


        .importzp rzbMask2
        .importzp rzbCtrl2
        .importzp zbCtrl2

        .importzp zbScrollX2
        .importzp zbScrollY2

        .importzp zaOamBuffer2


        .import ppu

        .import set_mask
        .import set_ctrl
        .import scroll
        .import dma_oam

        .import set_mask2
        .import set_ctrl2
        .import scroll2
        .import copy_oam2

        ; PPU registers
        CTRL     = $2000 ; VPHBSINN
        MASK     = $2001 ; BGRsbMmG
        STATUS   = $2002 ; VSO-----
        OAM_ADDR = $2003 ; OAM read/write address
        OAM_DATA = $2004 ; OAM data read/write
        SCROLL   = $2005 ; fine scroll position (two writes: X scroll, Y scroll)
        ADDR     = $2006 ; PPU read/write address (two writes: most significant byte, least significant byte)
        DATA     = $2007 ; PPU data read/write
        OAM_DMA  = $4014 ; OAM DMA high address

        ; PPU2 registers
        CTRL2     = $3000 ; VPHBSINN
        MASK2     = $3001 ; BGRsbMmG
        STATUS2   = $3002 ; VSO-----
        OAM_ADDR2 = $3003 ; OAM read/write address
        OAM_DATA2 = $3004 ; OAM data read/write
        SCROLL2   = $3005 ; fine scroll position (two writes: X scroll, Y scroll)
        ADDR2     = $3006 ; PPU read/write address (two writes: most significant byte, least significant byte)
        DATA2     = $3007 ; PPU data read/write

        ; PPU register flags / bit masks.

        ; PPU control register flags
        CTRL_V = %10000000 ; NMI enable
        CTRL_P = %01000000 ; PPU master/slave
        CTRL_H = %00100000 ; sprite height (0: 8x8 pixels; 1: 8x16 pixels)
        CTRL_B = %00010000 ; background pattern table select (0: $0000; 1: $1000)
        CTRL_S = %00001000 ; sprite pattern table select (0: $0000; 1: $1000; ignored in 8x16 mode)
        CTRL_I = %00000100 ; increment mode (0: add 1, going across; 1: add 32, going down)
        CTRL_N = %00000011 ; nametable select (0 = $2000; 1 = $2400; 2 = $2800; 3 = $2C00)

        ; NOTE: some of these symbols do not follow the normal upper case naming convention.
        ;       instead, they borrow from the naming convention used by nesdev.org.
        ;       https://www.nesdev.org/wiki/PPU_registers
        ;       the linter will complain about this
        ;       but *.inc files aren't linted at compile time so i'm ignoring it.

        ; PPU mask register flags
        MASK_B = %10000000 ; color emphasis blue
        MASK_G = %01000000 ; color emphasis green (red on PAL/Dendy)
        MASK_R = %00100000 ; color emphasis red (green on PAL/Dendy)
        MASK_s = %00010000 ; sprite enable
        MASK_b = %00001000 ; background enable
        MASK_M = %00000100 ; sprite left column enable
        MASK_m = %00000010 ; background left column enable
        MASK_g = %00000001 ; greyscale

        ; PPU status register flags
        STATUS_V = %10000000 ; vblank
        STATUS_S = %01000000 ; sprite 0 hit
        STATUS_O = %00100000 ; sprite overflow; read resets write pair for $2005/$2006

        PATTERN_0 = $0000
        PATTERN_1 = $1000

        NAMETABLE_0 = $2000
        NAMETABLE_1 = $2400
        NAMETABLE_2 = $2800
        NAMETABLE_3 = $2C00

        ATTRIBUTE_0 = $23C0
        ATTRIBUTE_1 = $27C0
        ATTRIBUTE_2 = $2BC0
        ATTRIBUTE_3 = $2FC0

        BACKGROUND_PALETTE = $3f00
        SPRITE_PALETTE = $3f10

        SPRITE_COUNT = 64
        SPRITE_COUNT2 = 8

        SPRITE_ATTR_V = %10000000
        SPRITE_ATTR_H = %01000000
        SPRITE_ATTR_B = %00100000
        SPRITE_ATTR_P = %00000011

        ; tile dimensions
        TILE_WIDTH_PIXELS = 8
        TILE_HEIGHT_PIXELS = 8

        ; screen dimensions in tiles
        SCREEN_WIDTH_TILES = 32
        SCREEN_HEIGHT_TILES = 30

        ; screen dimensions in pixels
        SCREEN_WIDTH_PIXELS = 256
        SCREEN_HEIGHT_PIXELS = 240

        .struct sSprite
            bPosY .byte
            bTile .byte
            bAttr .byte
            bPosX .byte
        .endstruct

        .enum eColor
            GRAY = $00
            DARK_AZURE = $01
            DARK_BLUE = $02
            DARK_VIOLET = $03
            DARK_MAGENTA = $04
            DARK_ROSE = $05
            DARK_RED = $06
            DARK_ORANGE = $07
            DARK_YELLOW = $08
            DARK_CHARTREUSE = $09
            DARK_GREEN = $0a
            DARK_SPRING = $0b
            DARK_CYAN = $0c
            DARK_BLACK = $0d ; do not use
            ; BLACK = $0e
            BLACK = $0f
            LIGHT_GRAY = $10
            AZURE = $11
            BLUE = $12
            VIOLET = $13
            MAGENTA = $14
            ROSE = $15
            RED = $16
            ORANGE = $17
            YELLOW = $18
            CHARTREUSE = $19
            GREEN = $1a
            SPRING = $1b
            CYAN = $1c
            ; BLACK = $1d
            ; BLACK = $1e
            ; BLACK = $1f
            WHITE = $20
            LIGHT_AZURE = $21
            LIGHT_BLUE = $22
            LIGHT_VIOLET = $23
            LIGHT_MAGENTA = $24
            LIGHT_ROSE = $25
            LIGHT_RED = $26
            LIGHT_ORANGE = $27
            LIGHT_YELLOW = $28
            LIGHT_CHARTREUSE = $29
            LIGHT_GREEN = $2a
            LIGHT_SPRING = $2b
            LIGHT_CYAN = $2c
            DARK_GRAY = $2d
            ; BLACK = $2e
            ; BLACK = $2f
            PALE_AZURE = $31
            PALE_BLUE = $32
            PALE_VIOLET = $33
            PALE_MAGENTA = $34
            PALE_ROSE = $35
            PALE_RED = $36
            PALE_ORANGE = $37
            PALE_YELLOW = $38
            PALE_CHARTREUSE = $39
            PALE_GREEN = $3a
            PALE_SPRING = $3b
            PALE_CYAN = $3c
            PALE_GRAY = $3d
            ; BLACK = $3e
            ; BLACK = $3f
        .endenum

    .endscope

.endif
