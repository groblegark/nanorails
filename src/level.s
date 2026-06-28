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
zwPtr:    .res 2
zbBiome:  .res 1
zwOutRem: .res 2    ; bytes left to emit while unpacking
zbWhich:  .res 1    ; 0 = PPU1 DATA, 1 = PPU2 DATA2
zbTmp:    .res 1

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
    lda #0
    sta zbWhich
    jsr unpack

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
    lda #1
    sta zbWhich
    jsr unpack

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

; read next source byte (zwPtr) into A, advance the 16-bit pointer. preserves X.
.proc getb
    ldy #0
    lda (zwPtr), y
    inc zwPtr
    bne :+
    inc zwPtr+1
:   rts
.endproc

; write A to the selected PPU data port and count one output byte. preserves X.
.proc putb
    ldy zbWhich
    beq :+
    sta Ppu::DATA2
    jmp cnt
:   sta Ppu::DATA
cnt:
    lda zwOutRem
    bne :+
    dec zwOutRem+1
:   dec zwOutRem
    rts
.endproc

; PackBits decode: zwPtr -> compressed stream, emit exactly 2048 bytes to the
; PPU port chosen by zbWhich. (encoder: tools/gen.py packbits())
.proc unpack
    lda #<2048
    sta zwOutRem
    lda #>2048
    sta zwOutRem+1
ctl:
    jsr getb                 ; control byte
    cmp #$80
    bcs run
    ; literal run: copy A+1 source bytes
    tax
    inx
lit:
    jsr getb
    jsr putb
    dex
    bne lit
    jmp more
run:
    eor #$ff
    clc
    adc #2                   ; X = 257 - C  (run length 2..128)
    tax
    jsr getb                 ; byte to repeat
    sta zbTmp
rl:
    lda zbTmp
    jsr putb
    dex
    bne rl
more:
    lda zwOutRem
    ora zwOutRem+1
    bne ctl
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
