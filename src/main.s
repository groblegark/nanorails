.include "main.inc"

.include "apu.inc"
.include "ppu.inc"
.include "nmi.inc"
.include "palette.inc"
.include "level.inc"
.include "train.inc"

.export main

.segment "CODE"

.proc main
    jsr Apu::apu
    jsr Ppu::ppu

    jsr Palette::palette
    jsr Level::level
    jsr Train::train

    ; PPU1 = front layer, NMI enabled.
    lda #Ppu::CTRL_V
    jsr Ppu::set_ctrl
    ; PPU2 = back layer (slave).
    lda #Ppu::CTRL_P
    jsr Ppu::set_ctrl2

    ; show background + sprites, including the leftmost 8px column.
    lda #(Ppu::MASK_s | Ppu::MASK_b | Ppu::MASK_m | Ppu::MASK_M)
    jsr Ppu::set_mask
    jsr Ppu::set_mask2

    ; [fall_through]
.endproc

.proc main_loop
    jsr Nmi::wait
    jsr Train::update
    jmp main_loop
.endproc
