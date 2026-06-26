
.ifndef _HEADER_
    _HEADER_ = 1

    .scope Header

        ; using one-based indexing since it will be more understandable in the Makefile.
        ; https://www.nesdev.org/wiki/INES
        ; https://www.nesdev.org/wiki/NES_2.0
        .enum eType
            INES = 1
            NES2 = 2
        .endenum

        .enum eMirror
            HORIZONTAL
            VERTICAL
        .endenum

        ; https://www.nesdev.org/wiki/Mapper
        .enum eMapper
            NROM  = 0
            MMC1  = 1
            MMC3  = 4
            MMC5  = 5
            MMC2  = 9
            MMC4  = 10
        .endenum

        ; https://www.nesdev.org/wiki/NES_2.0#Default_Expansion_Device
        .enum eDevice
            NONE = $00
            FAMILY_BASIC_KEYBOARD = $23
        .endenum
        
        .ifndef TYPE
            TYPE = eType::NES2
        .endif

        ; common iNes/NES 2.0 header settings

        PRG_ROM   = $8000   ; PRG ROM in bytes
        CHR_ROM   = $2000   ; CHR ROM in bytes
        MIRROR    = eMirror::VERTICAL
        SRAM      = 0       ; 1 = battery backed save RAM at $6000-7FFF
        TRAINER   = 0       ; 1 = 512-byte trainer data
        ALT_NAM   = 0       ; 1 = alternative nametable layout
        MAPPER    = eMapper::NROM
        PRG_RAM   = 0       ; PRG RAM in bytes
        CONSOLE   = 0       ; 0 = NES/Famicom
                            ; 1 = Vs. System
                            ; 2 = Playchoice 10
                            ; 3 = extended console type (NES 2.0 header only)
        TIMING    = 0       ; 0: NTSC NES
                            ; 1: PAL NES
                            ; 2: Multi-region (NES 2.0 header only)
                            ; 3: Dendy (NES 2.0 header only)

        ; exclusive NES 2.0 header settings

        PRG_NVRAM = 0       ; PRG NVRAM in bytes
        CHR_RAM   = 0       ; CHR RAM in bytes
        CHR_NVRAM = 0       ; CHR NVRAM in bytes

        SUBMAPPER = 0       ; mapper variant
        DEVICE    = eDevice::NONE

        ; NES 2.0 headers represent some numbers as 64 times a power of 2.
        ; this macro will convert a number in bytes to that power.
        ; < bytes = size of a memory region measured in bytes.
        ; > power = power of 2 times 64 that equals the specified number of bytes.
        ;           if bytes is 0 then power will be 0.
        ;           if bytes is an invalid number then power will be -1.
        .macro bytes_to_power bytes, power
            .local bytes
            .local power
            .local count

            power .set -1

            .if bytes = 0
                power .set 0
            .else
                .repeat 15, count
                    .if bytes = 64 << (count + 1)
                        power .set (count + 1)
                    .endif
                .endrepeat

                .if power = -1
                    .error "cannot convert bytes to power of 2 times 64"
                .endif
            .endif
        .endmacro

    .endscope

.endif
