
.include "rand.inc"

.exportzp rzbPrng

.export init_prng
.export tick_prng

.segment "ZEROPAGE"

rzbPrng:
zwSeed: .res 2

.segment "CODE"

; Initialize the pseudo-random number generator.
; < A = seed low byte
; < Y = seed high byte
; > A = pseudo-random number in the range [0-255].
; changes: A, Y
.proc init_prng
    sta zwSeed
    sty zwSeed+1
    ; [fall_through]
.endproc

; Tick the pseudo-random number generator.
; zwSeed must be initialized with a non-zero value before the first call to this function.
; https://www.nesdev.org/wiki/Random_number_generator?utm_source=chatgpt.com#Simple
; > A = pseudo-random number in the range [0-255].
; > C = always set
; > Z = set if A = 0
; > N = set if A.7 set set
; changes: A, Y
.proc tick_prng
    lda zwSeed+0
    ldy #8 ; iteration count (generates 8 bits)

shift_loop:
    ; shift the 16-bit seed value
    asl
    rol zwSeed+1
    bcc check_if_done; branch if zwSeed.15 was 0
    eor #$39
check_if_done:
    dey
    bne shift_loop

    sta zwSeed+0
    cmp #0     ; reload flags
    rts
.endproc
