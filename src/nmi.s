
.include "nmi.inc"

.include "ppu.inc"

.export nmi
.export wait
.exportzp rzbNmiCount
.exportzp zbSkyColor

.segment "ZEROPAGE"

rzbNmiCount:
zbNmiCount: .res 1

; day/night backdrop colour, written to $3F00 every v-blank.
zbSkyColor: .res 1

.segment "CODE"

; global NMI handler
.proc nmi
    ; save CPU state
    pha ; save A register
    txa
    pha ; save X register
    tya
    pha ; save Y register


    jsr Ppu::dma_oam
    jsr Ppu::copy_oam2

    ; day/night: update the universal backdrop colour on both PPUs.
    ; must precede scroll (it disturbs the $2006/$2005 latch).
    lda #$3f
    sta Ppu::ADDR
    sta Ppu::ADDR2
    lda #$00
    sta Ppu::ADDR
    sta Ppu::ADDR2
    lda zbSkyColor
    sta Ppu::DATA
    sta Ppu::DATA2

    jsr Ppu::scroll
    jsr Ppu::scroll2

    ; alert "wait" that an NMI finished.
    inc zbNmiCount

    ; restore CPU state
    pla ; restore Y register
    tay
    pla ; restore X register
    tax
    pla ; restore A register

    rti
.endproc


; wait for an NMI to occur and finish.
; upon return, we may or may not still be in v-blank.
; changes: A
.proc wait
    lda zbNmiCount
loop:
    ; NMI will increment this to break us out of the loop.
    cmp zbNmiCount
    beq loop
    rts
.endproc
