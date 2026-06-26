
.include "input.inc"

.exportzp rzbJoypad1

.export read_joypad1

.segment "ZEROPAGE"

rzbJoypad1:
zbJoypad1: .res 1

.segment "CODE"

; read joypad 1
; changes: A
.proc read_joypad1
    lda #$01
    ; load the joypad's shift register
    sta Input::JOYPAD1
    sta zbJoypad1
    lsr ; A is now 0
    ; latch the joypad's shift register
    sta Input::JOYPAD1
loop:
    lda Input::JOYPAD1
    lsr a
    rol zbJoypad1
    bcc loop
    rts
.endproc
