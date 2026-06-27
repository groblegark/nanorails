.include "level.inc"
.include "ppu.inc"
.include "nmi.inc"
.include "gen.inc"

.import rbaNearLo
.import rbaNearHi
.import rbaFarLo
.import rbaFarHi
.import aBiomePal

.export level
.export load_biome

.segment "ZEROPAGE"
zwPtr:   .res 2
zbBiome: .res 1

.segment "CODE"

; init both PPUs' pattern tables, then load biome 0.
.proc level
    jsr init_patterns
    lda #0
    jsr load_biome
    rts
.endproc

; A = biome index. Rewrites PPU1 + PPU2 nametables and the BG palette, and sets
; the sky backdrop shadow. MUST run with rendering AND NMI disabled (it does a
; lot of VRAM writes); the caller is responsible for that.
.proc load_biome
    sta zbBiome

    ; --- near world -> PPU1 ---
    lda #>Ppu::NAMETABLE_0
    sta Ppu::ADDR
    lda #<Ppu::NAMETABLE_0
    sta Ppu::ADDR
    ldx zbBiome
    lda rbaNearLo, x
    sta zwPtr
    lda rbaNearHi, x
    sta zwPtr+1
    jsr copy_2k_ppu1

    ; --- far world -> PPU2 ---
    lda #>Ppu::NAMETABLE_0
    sta Ppu::ADDR2
    lda #<Ppu::NAMETABLE_0
    sta Ppu::ADDR2
    ldx zbBiome
    lda rbaFarLo, x
    sta zwPtr
    lda rbaFarHi, x
    sta zwPtr+1
    jsr copy_2k_ppu2

    ; --- BG palette: src = aBiomePal + biome*16 ---
    lda zbBiome
    asl
    asl
    asl
    asl                      ; *16 (biome < 8 -> no carry)
    clc
    adc #<aBiomePal
    sta zwPtr
    lda #>aBiomePal
    adc #0
    sta zwPtr+1

    lda #>Ppu::BACKGROUND_PALETTE
    sta Ppu::ADDR
    sta Ppu::ADDR2
    lda #<Ppu::BACKGROUND_PALETTE
    sta Ppu::ADDR
    sta Ppu::ADDR2
    ldy #0
pal_loop:
    lda (zwPtr), y
    sta Ppu::DATA
    sta Ppu::DATA2
    iny
    cpy #16
    bne pal_loop

    ; keep the per-frame NMI backdrop write in sync with this biome's sky
    ldy #0
    lda (zwPtr), y
    sta Nmi::zbSkyColor
    rts
.endproc

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

.proc init_patterns
    lda #>Ppu::PATTERN_0
    sta Ppu::ADDR
    sta Ppu::ADDR
    sta Ppu::ADDR2
    sta Ppu::ADDR2
    lda Ppu::DATA
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
