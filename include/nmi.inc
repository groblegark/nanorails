
.ifndef _NMI_
    _NMI_ = 1

    .scope Nmi

        .import nmi
        .import wait
        .importzp rzbNmiCount
        .importzp zbSkyColor

    .endscope

.endif
