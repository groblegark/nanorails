.include "level.inc"
.include "ppu.inc"

.import rbaNear
.import rbaFar

.export level

.segment "ZEROPAGE"

zwPtr: .res 2

.segment "CODE"

; load both layers' nametables. caller enables rendering afterwards.
.proc level
    jsr init_patterns

    ; --- near town -> PPU1, nametables 0 & 1 ($2000-$27FF) ---
    lda #>Ppu::NAMETABLE_0
    sta Ppu::ADDR
    lda #<Ppu::NAMETABLE_0
    sta Ppu::ADDR

    lda #<rbaNear
    sta zwPtr
    lda #>rbaNear
    sta zwPtr+1
    jsr copy_2k_ppu1

    ; --- far skyline -> PPU2, nametables 0 & 1 ($2000-$27FF) ---
    lda #>Ppu::NAMETABLE_0
    sta Ppu::ADDR2
    lda #<Ppu::NAMETABLE_0
    sta Ppu::ADDR2

    lda #<rbaFar
    sta zwPtr
    lda #>rbaFar
    sta zwPtr+1
    jsr copy_2k_ppu2

    rts
.endproc

; copy 2048 bytes from (zwPtr) to PPU1 data port.
.proc copy_2k_ppu1
    ldx #8
    ldy #0
loop:
    lda (zwPtr), y
    sta Ppu::DATA
    iny
    bne loop
    inc zwPtr+1
    dex
    bne loop
    rts
.endproc

; copy 2048 bytes from (zwPtr) to PPU2 data port.
.proc copy_2k_ppu2
    ldx #8
    ldy #0
loop:
    lda (zwPtr), y
    sta Ppu::DATA2
    iny
    bne loop
    inc zwPtr+1
    dex
    bne loop
    rts
.endproc

; copy pattern table 0 from PPU1 CHR into PPU2 pattern RAM.
.proc init_patterns
    lda #>Ppu::PATTERN_0
    sta Ppu::ADDR
    sta Ppu::ADDR
    sta Ppu::ADDR2
    sta Ppu::ADDR2

    lda Ppu::DATA ; dummy read to prime the PPU read buffer
    ldx #0
    ldy #16
loop:
    lda Ppu::DATA
    sta Ppu::DATA2
    dex
    bne loop
    dey
    bne loop
    rts
.endproc
