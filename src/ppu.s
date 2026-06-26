
.include "ppu.inc"

.include "chr.inc"
.include "nmi.inc"
.include "const.inc"

.import __OAM_LOAD__

; export PPU shadow values as read-only.
; values should be updated through well-defined interfaces.
.exportzp rzbMask
.exportzp rzbCtrl
.exportzp zbCtrl

.exportzp zbScrollX
.exportzp zbScrollY

.export aOamBuffer


.exportzp rzbDualPpu


.exportzp rzbMask2
.exportzp rzbCtrl2
.exportzp zbCtrl2

.exportzp zbScrollX2
.exportzp zbScrollY2

.export zaOamBuffer2

.export ppu

.export set_mask
.export set_ctrl
.export scroll
.export dma_oam

.export set_mask2
.export set_ctrl2
.export scroll2
.export copy_oam2

.segment "ZEROPAGE"

; Ppu::MASK shadow
rzbMask:
zbMask: .res 1

; Ppu::CTRL shadow
rzbCtrl:
zbCtrl: .res 1

; dual PPU flag.
; 0 = single PPU
; 1 = dual PPUs
rzbDualPpu:
zbDualPpu: .res 1

; Ppu::MASK2 shadow
rzbMask2:
zbMask2: .res 1

; Ppu::CTRL2 shadow
rzbCtrl2:
zbCtrl2: .res 1

; screen x and y scroll position, relative to the current nametable.
zbScrollX: .res 1
zbScrollY: .res 1

zbScrollX2: .res 1
zbScrollY2: .res 1

; sprite data
zaOamBuffer2: .res .sizeof(Ppu::sSprite) * Ppu::SPRITE_COUNT2

.segment "OAM"

; sprite data
aOamBuffer: .res .sizeof(Ppu::sSprite) * Ppu::SPRITE_COUNT

.segment "BSS"


.segment "CODE"

; =============================================================================
; public functions
; =============================================================================

; initialize PPU(s)
; changes: A
.proc ppu
    lda #0
    jsr set_ctrl
    jsr set_ctrl2
    jsr set_mask
    jsr set_mask2

    jsr dual_ppu
    beq ppu1

    jsr ppu2
    ; [fall_through]
.endproc

; initialize PPU1
.proc ppu1
    rts
.endproc

; initialize PPU2
.proc ppu2
    rts
.endproc

; check if we're running a dual PPU configuration and set the zbDualPpu flag.
; > A = 0 if single PPU
;   A = 1 if dual PPU
; > Z = 1 if single PPU
;   Z = 0 if dual PPU
; changes: A
.proc dual_ppu
    ; write 1 to the nametable of PPU1.
    lda #>Ppu::NAMETABLE_0
    sta Ppu::ADDR
    lda #<Ppu::NAMETABLE_0
    sta Ppu::ADDR

    lda #1
    sta Ppu::DATA

    ; write 0 to the nametable of what might be PPU2.
    lda #>Ppu::NAMETABLE_0
    sta Ppu::ADDR2
    lda #<Ppu::NAMETABLE_0
    sta Ppu::ADDR2

    lda #0
    sta Ppu::DATA2

    ; read nametable data from PPU1.
    lda #>Ppu::NAMETABLE_0
    sta Ppu::ADDR
    lda #<Ppu::NAMETABLE_0
    sta Ppu::ADDR

    lda Ppu::DATA ; dummy read
    ; A = 0 if single PPU
    ; A = 1 if dual PPU
    lda Ppu::DATA
    sta zbDualPpu
    rts
.endproc

; set the PPU MASK value and update the shadow copy.
; < A = new PPU mask value.
.proc set_mask
    sta Ppu::MASK
    sta zbMask
    rts
.endproc

; set the PPU CTRL value and update the shadow copy.
; < A = new PPU CTRL value.
.proc set_ctrl
    sta Ppu::CTRL
    sta zbCtrl
    rts
.endproc

; set the PPU MASK2 value and update the shadow copy.
; < A = new PPU MASK2 value.
.proc set_mask2
    sta Ppu::MASK2
    sta zbMask2
    rts
.endproc

; set the PPU CTRL2 value and update the shadow copy.
; < A = new PPU CTRL2 value.
.proc set_ctrl2
    sta Ppu::CTRL2
    sta zbCtrl2
    rts
.endproc

; scroll the viewable portion of the screen to the x and y offsets,
; given by zbScrollX and zbScrollY, of the currently selected nametable.
; this function is intended to be called from "nmi" during v-blank.
; changes: A
.proc scroll
    lda zbCtrl
    sta Ppu::CTRL
    lda zbScrollX
    sta Ppu::SCROLL
    lda zbScrollY
    sta Ppu::SCROLL
    rts
.endproc

; scroll the viewable portion of the screen to the x and y offsets,
; given by zbScrollX and zbScrollY, of the currently selected nametable.
; this function is intended to be called from "nmi" during v-blank.
; changes: A
.proc scroll2
    lda zbCtrl2
    sta Ppu::CTRL2
    lda zbScrollX2
    sta Ppu::SCROLL2
    lda zbScrollY2
    sta Ppu::SCROLL2
    rts
.endproc


; copy shadow OAM to PPU1 via DMA.
; this function is intended to be called from "nmi" during v-blank.
; changes: A
.proc dma_oam
    lda #0
    sta Ppu::OAM_ADDR
    lda #>__OAM_LOAD__
    sta Ppu::OAM_DMA
    rts
.endproc

; copy shadow OAM2 to PPU2 via manual write.
; this function is intended to be called from "nmi" during v-blank.
; changes: A, X
.proc copy_oam2
    ; start at address 0.
    ; we're going to re-write all of OAM to prevent any glitches.
    lda #0
    sta Ppu::OAM_ADDR2

    ; we don't have enough time for a full shadow OAM copy
    ; so we'll limit the usable sprites and keep their shadow copy in zeropage.
    .repeat .sizeof(Ppu::sSprite) * Ppu::SPRITE_COUNT2, i
        lda zaOamBuffer2+i
        sta Ppu::OAM_DATA2
    .endrepeat

    ; efficiently move the remaining unused sprites off screen.
    lda #<(Ppu::SCREEN_HEIGHT_PIXELS + Ppu::TILE_HEIGHT_PIXELS)

    .repeat .sizeof(Ppu::sSprite) * (Ppu::SPRITE_COUNT - Ppu::SPRITE_COUNT2)
        sta Ppu::OAM_DATA2
    .endrepeat

    rts
.endproc
