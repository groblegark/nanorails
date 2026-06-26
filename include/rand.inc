
.ifndef _RAND_
    _RAND = 1

    .scope Rand

        .importzp rzbPrng

        .import init_prng
        .import tick_prng

    .endscope

.endif
