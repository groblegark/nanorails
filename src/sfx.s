.include "sfx.inc"

.export sfx_init
.export sfx_update
.export sfx_whistle
.export sfx_bell
.export sfx_chuff
.export sfx_brake

; raw APU registers
PULSE1   = $4000
PULSE2   = $4004
NOISE    = $400C
APUSTAT  = $4015

WHISTLE_LEN = 36
BELL_LEN    = 26
CHUFF_LEN   = 5
BRAKE_LEN   = 3

.segment "ZEROPAGE"
sfxWhistle: .res 1
sfxBell:    .res 1
sfxChuff:   .res 1
sfxBrake:   .res 1

.segment "CODE"

.proc sfx_init
    lda #$0f
    sta APUSTAT          ; enable pulse1, pulse2, triangle, noise
    lda #$08
    sta PULSE1 + 1       ; sweep off
    sta PULSE2 + 1
    lda #0
    sta sfxWhistle
    sta sfxBell
    sta sfxChuff
    sta sfxBrake
    lda #$b0             ; duty2, halt, constant vol, vol 0
    sta PULSE1
    sta PULSE2
    lda #$30
    sta NOISE
    rts
.endproc

; --- triggers ---------------------------------------------------------------
.proc sfx_whistle
    lda #WHISTLE_LEN
    sta sfxWhistle
    lda #$8c             ; pulse1 low tone (~790 Hz)
    sta PULSE1 + 2
    lda #$00
    sta PULSE1 + 3
    lda #$5e             ; pulse2 high tone (~1180 Hz)
    sta PULSE2 + 2
    lda #$00
    sta PULSE2 + 3
    rts
.endproc

.proc sfx_bell
    lda #BELL_LEN
    sta sfxBell
    lda #$50             ; ding (~1385 Hz)
    sta PULSE2 + 2
    lda #$00
    sta PULSE2 + 3
    rts
.endproc

.proc sfx_chuff
    lda #CHUFF_LEN
    sta sfxChuff
    rts
.endproc

.proc sfx_brake
    lda #BRAKE_LEN
    sta sfxBrake
    rts
.endproc

; --- per-frame mixer --------------------------------------------------------
.proc sfx_update
    ; PULSE1: whistle low tone
    lda sfxWhistle
    beq p1off
    dec sfxWhistle
    lda sfxWhistle
    lsr
    cmp #16
    bcc :+
    lda #15
:
    ora #$b0
    sta PULSE1
    jmp p1done
p1off:
    lda #$b0
    sta PULSE1
p1done:

    ; PULSE2: whistle high tone (priority) else station bell
    lda sfxWhistle
    beq p2bell
    lda sfxWhistle
    lsr
    cmp #16
    bcc :+
    lda #15
:
    ora #$b0
    sta PULSE2
    jmp p2done
p2bell:
    lda sfxBell
    beq p2off
    dec sfxBell
    lda sfxBell
    lsr
    cmp #16
    bcc :+
    lda #15
:
    ora #$b0
    sta PULSE2
    jmp p2done
p2off:
    lda #$b0
    sta PULSE2
p2done:

    ; NOISE: brake hiss (priority) else exhaust chuff
    lda sfxBrake
    beq nchuff
    dec sfxBrake
    lda #$03
    sta NOISE + 2
    lda #$35             ; constant vol, soft
    sta NOISE
    lda #$00
    sta NOISE + 3
    jmp ndone
nchuff:
    lda sfxChuff
    beq noff
    dec sfxChuff
    lda #$07             ; airy noise period
    sta NOISE + 2
    lda sfxChuff
    asl
    asl
    cmp #16
    bcc :+
    lda #15
:
    ora #$30
    sta NOISE
    lda #$00
    sta NOISE + 3
    jmp ndone
noff:
    lda #$30
    sta NOISE
ndone:
    rts
.endproc
