
.ifndef _CONST_
    _CONST_ = 1

    .scope Const

        ZERO_PAGE = $00

    .endscope

    ; CPU ignores the following 1 or 2 bytes
    .define SKIP_BYTE .byte $24 ; 8-bit BIT instruction.
    .define SKIP_WORD .byte $2c ; 16-bit BIT instruction.
    .define KILL .byte $02 ; halt and catch fire.

.endif
