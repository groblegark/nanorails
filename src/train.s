.include "train.inc"
.include "ppu.inc"
.include "nmi.inc"
.include "input.inc"
.include "sfx.inc"
.include "level.inc"
.include "gen.inc"

.import rbaTrainBody
.import rbaWheelDX

.export train
.export update

; ---- screen placement -------------------------------------------------------
BASE_X = 80
BASE_Y = 168
CHIM_X = BASE_X + Gen::CHIMNEY_DX
CHIM_Y = BASE_Y + Gen::CHIMNEY_DY

; ---- OAM slot allocation ----------------------------------------------------
; ALL coaches ride PPU1 (front) so they never duck behind the near-town. To
; beat the 8-sprites-per-scanline limit on the crowded loco Y band, the coach
; metasprites are sprite-MULTIPLEXED: the loco body + wheels + gauge + smoke
; stay at fixed low OAM slots (never flicker), and the N coaches are laid into
; the coach slot block in an order ROTATED by the frame counter. The PPU's
; "first 8 by OAM index" rule then drops a DIFFERENT coach each frame, so all
; coaches shimmer evenly instead of the rear ones vanishing permanently.
PPU1_CARS  = Gen::MAX_CARS                       ; ALL coaches on PPU1 (front)
WHEEL_BASE = Gen::TRAIN_BODY_COUNT
CAR_BASE   = WHEEL_BASE + Gen::WHEEL_COUNT       ; PPU1 coaches: PPU1_CARS * 4
SMOKE_BASE = CAR_BASE + PPU1_CARS * 4
METER_BASE = SMOKE_BASE + Gen::SMOKE_COUNT
PAX_BASE   = METER_BASE + Gen::METER_SEGS
USED       = PAX_BASE + 2
OAM = Ppu::aOamBuffer
OAM2 = Ppu::zaOamBuffer2                         ; PPU2 sprite shadow (zeropage)
ACCEL_STEP = 3

; ---- self-driving tuning (speed in 1/16 px/frame) --------------------------
VMAX       = 48
VBOOST     = 72
ACCEL      = 1
DECEL      = 2
BRAKE_HARD = 3
MIN_CREEP  = 8
DWELL_TIME = 240        ; ~4s at the platform
; trip = 85 * 256 px ~= 2 minutes of cruising. odd multiple -> alternate depots.
TRIP_HI    = 85
CHUFF_GAP  = 64        ; px between exhaust chuffs (~21 frames apart at cruise;
                       ; must exceed CHUFF_LEN*pxStep or chuffs merge into a drone)
THROTTLE   = Input::JOYPAD_A | Input::JOYPAD_RIGHT
BRAKEBTN   = Input::JOYPAD_B | Input::JOYPAD_LEFT

.segment "ZEROPAGE"
spd:      .res 1
acc:      .res 1
odoL:     .res 1
odoH:     .res 1
togoL:    .res 1
togoH:    .res 1
mode:     .res 1
dwell:    .res 1
desired:  .res 1
pxStep:   .res 1
tmpH:     .res 1
zbBaseY:  .res 1
zbWheelY: .res 1
zbWTile:  .res 1
zbSmokeClock: .res 1
zbPmask:  .res 1
zbTmp:    .res 1
zbLit:    .res 1
zbMeterX: .res 1
lastChuff: .res 1
todcL:    .res 1
todcH:    .res 1
paxX:     .res 1
carCount: .res 1
carDir:   .res 1
accelCtr: .res 1
carX:     .res 1
zbTmp2:   .res 1
capL:     .res 1
capH:     .res 1
arrivals: .res 1     ; count of station arrivals (exported to $0705)
zMod:     .res 1     ; per-frame coach rotation offset (multiplexing)
zCoach:   .res 1     ; logical coach index during slot fill
cptr:     .res 2     ; dest pointer for a coach metasprite (PPU1 OAM)
curBiome: .res 1     ; current biome/location index (exported to $0706)
prevUp:   .res 1     ; previous Up-button state (whistle edge detect)
prevDown: .res 1     ; previous Down-button state (bell edge detect)

.segment "RODATA"
; day -> noon -> sunset -> dusk -> night -> deep -> dawn -> morning
skyTable:
.byte $22, $2c, $27, $17, $05, $0f, $01, $11

.segment "CODE"

; =============================================================================
.proc train
    lda #$f0
    ldx #(USED * 4)
clr:
    sta OAM, x
    inx
    bne clr

    lda #0
    sta spd
    sta acc
    sta odoL
    sta odoH
    sta togoL
    sta togoH
    sta mode
    sta zbSmokeClock
    sta lastChuff
    sta todcL
    sta todcH
    sta carCount
    sta arrivals
    sta curBiome
    sta prevUp
    sta prevDown
    lda #1
    sta carDir
    sta accelCtr
    lda #DWELL_TIME
    sta dwell
    ; sky backdrop is set by Level::load_biome (called from level init)

    jsr Sfx::sfx_init
    jsr draw_all
    rts
.endproc

; =============================================================================
.proc update
    jsr Input::read_joypad1

    ; manual whistle: toot on a fresh Up press (rising edge)
    lda Input::rzbJoypad1
    and #Input::JOYPAD_UP
    tay                      ; Y = current Up state (0 or 8)
    beq whistle_done
    lda prevUp
    bne whistle_done         ; was already held
    jsr Sfx::sfx_whistle
whistle_done:
    sty prevUp

    ; manual bell: ding on a fresh Down press (rising edge)
    lda Input::rzbJoypad1
    and #Input::JOYPAD_DOWN
    tay                      ; Y = current Down state (0 or 4)
    beq bell_done
    lda prevDown
    bne bell_done            ; was already held
    jsr Sfx::sfx_bell
bell_done:
    sty prevDown

    lda mode
    bne do_run
    jsr dwell_state
    jmp after
do_run:
    jsr run_state
after:
    jsr apply_scroll
    jsr draw_all
    jsr export_state         ; publish live state to $0700-$0705 for the host
    jsr Sfx::sfx_update
    rts
.endproc

; ----------------------------------------------------------------------------
.proc dwell_state
    lda #0
    sta spd

    lda Input::rzbJoypad1
    and #THROTTLE
    bne depart
    dec dwell
    bne done
depart:
    lda #1
    sta mode
    lda #0
    sta togoL
    lda #TRIP_HI
    sta togoH
    jsr Sfx::sfx_whistle    ; toot on departure
done:
    rts
.endproc

; ----------------------------------------------------------------------------
.proc run_state
    lda #VMAX
    sta desired
    lda Input::rzbJoypad1
    and #THROTTLE
    beq have_desired
    lda #VBOOST
    sta desired
have_desired:
    lda spd
    cmp desired
    bcs ge_desired
    ; accelerate, throttled by car mass (period = 1 + carCount*2)
    dec accelCtr
    bne ramped               ; not time to bump this frame -> keep speed
    lda carCount
    asl
    clc
    adc #1
    sta accelCtr
    lda spd
    clc
    adc #ACCEL_STEP
    cmp desired
    bcc store
    lda desired
    jmp store
ge_desired:
    beq ramped
    sec
    sbc #DECEL
    cmp desired
    bcs store
    lda desired
store:
    sta spd
ramped:
    ; brake cap: heavier trains begin slowing from farther out.
    ; cap = togo >> carCount, clamped to 255.
    lda togoL
    sta capL
    lda togoH
    sta capH
    lda carCount             ; brake-distance mass effect, shift capped at 2
    cmp #3
    bcc shift_ok
    lda #2
shift_ok:
    tax
    beq capdone
capsh:
    lsr capH
    ror capL
    dex
    bne capsh
capdone:
    lda capH
    beq capuselo
    lda #255
    jmp have_cap
capuselo:
    lda capL
have_cap:
    cmp spd
    bcs no_cap
    sta spd
no_cap:
    ; guarantee progress: while any distance remains, hold at least a creep
    ; speed so the final pixels always complete (else a loaded train freezes
    ; one pixel short of the platform forever).
    lda togoL
    ora togoH
    beq creep_done           ; arrived
    lda spd
    cmp #MIN_CREEP
    bcs creep_done
    lda #MIN_CREEP
    sta spd
creep_done:
    lda Input::rzbJoypad1
    and #BRAKEBTN
    beq braked
    lda spd
    sec
    sbc #BRAKE_HARD
    bcs pbrk
    lda #0
pbrk:
    sta spd
    jsr Sfx::sfx_brake
braked:
    jsr step_physics

    ; exhaust chuff, paced by distance rolled
    lda spd
    beq no_chuff
    lda odoL
    sec
    sbc lastChuff
    cmp #CHUFF_GAP
    bcc no_chuff
    lda odoL
    sta lastChuff
    jsr Sfx::sfx_chuff
no_chuff:
    ; brake hiss in the stopping zone
    lda togoH
    bne no_hiss
    lda togoL
    cmp #48
    bcs no_hiss
    lda spd
    beq no_hiss
    jsr Sfx::sfx_brake
no_hiss:

    ; arrived?
    lda togoL
    ora togoH
    bne done
    lda #0
    sta spd
    sta mode
    lda #DWELL_TIME
    sta dwell
    inc arrivals            ; arrived at a station
    jsr Sfx::sfx_bell       ; ding at the station

    ; advance to the next biome/location and swap the world in.
    inc curBiome
    lda curBiome
    cmp #Gen::BIOME_COUNT
    bcc biome_ok
    lda #0
    sta curBiome
biome_ok:
    jsr swap_biome

    ; couple/uncouple one car: ramp 0..MAX..0 so each leg has a different mass.
    lda carCount
    clc
    adc carDir
    sta carCount
    cmp #Gen::MAX_CARS
    bcc chk_zero
    lda #Gen::MAX_CARS      ; hit the cap -> start dropping cars
    sta carCount
    lda #$ff
    sta carDir
    jmp done
chk_zero:
    lda carCount
    bne done
    lda #1                 ; empty -> start adding cars
    sta carDir
done:
    rts
.endproc

; rewrite the world for curBiome. Disables NMI + rendering during the heavy
; VRAM rewrite (one blank frame), then restores them from the shadows.
.proc swap_biome
    lda Ppu::zbCtrl
    and #<~Ppu::CTRL_V
    sta Ppu::CTRL            ; NMI off (leave shadow intact)
    lda Ppu::zbCtrl2
    and #<~Ppu::CTRL_V
    sta Ppu::CTRL2
    lda #0
    sta Ppu::MASK           ; rendering off
    sta Ppu::MASK2

    lda curBiome
    jsr Level::load_biome

    lda Ppu::rzbMask
    sta Ppu::MASK           ; rendering back on
    lda Ppu::rzbMask2
    sta Ppu::MASK2
    lda Ppu::zbCtrl
    sta Ppu::CTRL           ; NMI back on
    lda Ppu::zbCtrl2
    sta Ppu::CTRL2
    rts
.endproc

.proc step_physics
    lda acc
    clc
    adc spd
    sta acc
    lsr
    lsr
    lsr
    lsr
    sta pxStep
    lda acc
    and #$0f
    sta acc

    lda togoH
    bne move
    lda togoL
    cmp pxStep
    bcs move
    sta pxStep
move:
    lda odoL
    clc
    adc pxStep
    sta odoL
    bcc o1
    inc odoH
o1:
    lda togoL
    sec
    sbc pxStep
    sta togoL
    bcs t1
    dec togoH
t1:
    rts
.endproc

.proc apply_scroll
    lda odoL
    sta Ppu::zbScrollX
    lda Ppu::zbCtrl
    and #%11111110
    sta Ppu::zbCtrl
    lda odoH
    and #1
    ora Ppu::zbCtrl
    sta Ppu::zbCtrl

    lda odoH
    lsr
    sta tmpH
    lda odoL
    ror
    sta Ppu::zbScrollX2
    lda Ppu::zbCtrl2
    and #%11111110
    sta Ppu::zbCtrl2
    lda tmpH
    and #1
    ora Ppu::zbCtrl2
    sta Ppu::zbCtrl2
    rts
.endproc

; =============================================================================
.proc draw_all
    ; smoke clock advances faster with speed (idle still wisps).
    lda spd
    lsr
    lsr
    lsr
    lsr
    clc
    adc #1
    adc zbSmokeClock
    sta zbSmokeClock

    ; chug bob only while moving
    lda #0
    sta zbBaseY
    lda spd
    beq no_bob
    lda odoL
    lsr
    lsr
    and #1
    sta zbBaseY
no_bob:
    lda zbBaseY
    clc
    adc #BASE_Y
    sta zbBaseY

    jsr install_body
    jsr install_wheels
    jsr install_cars
    jsr install_smoke
    jsr install_meter
    jsr install_pax
    jsr export_state
    rts
.endproc

; ----------------------------------------------------------------------------
; State export: copy game state to fixed RAM so a host can read it each frame.
;   $0700 = mode (0=dwell, 1=run)
;   $0701 = carCount
;   $0702 = odoL   $0703 = odoH   (16-bit odometer)
;   $0704 = spd
;   $0705 = arrivals (incremented once per station arrival)
.proc export_state
    lda mode
    sta $0700
    lda carCount
    sta $0701
    lda odoL
    sta $0702
    lda odoH
    sta $0703
    lda spd
    sta $0704
    lda arrivals
    sta $0705
    lda curBiome
    sta $0706
    rts
.endproc

; coupled passenger coaches trailing behind the locomotive.
;
; All coaches live in the PPU1 coach slot block (CAR_BASE..CAR_BASE+MAX_CARS).
; To beat the 8-sprites-per-scanline limit we MULTIPLEX: each frame we rotate
; which slot each logical coach occupies, so the PPU's "first 8 by OAM index"
; rule drops a different coach every frame -> even, gentle flicker.
;
; For slot s (0..carCount-1) we draw logical coach i = (s + frame) % carCount,
; where each logical coach i has its own X position in the train. Coaches with
; index >= carCount (and the PPU2 buffer) are parked off-screen.
.proc install_cars
    ; coach rows share the loco's Y band
    clc
    lda zbBaseY
    adc #8
    sta zbTmp                ; coach top Y
    clc
    adc #8
    sta zbTmp2               ; coach bottom Y

    ; park every coach slot first; then fill the active ones.
    ldx #0
park_loop:
    txa
    asl
    asl
    asl
    asl
    clc
    adc #<(OAM + CAR_BASE * 4)
    sta cptr
    lda #>(OAM + CAR_BASE * 4)
    adc #0
    sta cptr+1
    jsr park_coach
    inx
    cpx #Gen::MAX_CARS
    bne park_loop

    ; also keep the (now unused) PPU2 coach buffer parked off-screen.
    ldx #0
park2_loop:
    txa
    asl
    asl
    asl
    asl
    clc
    adc #<OAM2
    sta cptr
    lda #>OAM2
    adc #0
    sta cptr+1
    jsr park_coach
    inx
    cpx #2                   ; PPU2 shadow holds only 8 sprites (2 coach units)
    bne park2_loop

    lda carCount
    beq carsdone             ; no coaches -> nothing to draw

    ; frameMod = frame % carCount  (carCount <= 5, so subtract in a loop)
    lda Nmi::rzbNmiCount
fmod:
    cmp carCount
    bcc fmod_done
    sec
    sbc carCount
    jmp fmod
fmod_done:
    sta zMod                 ; per-frame rotation offset = frame % carCount
    ldx #0                   ; slot index s
sloop:
    ; logical coach i = (s + frameMod) % carCount
    txa
    clc
    adc zMod
    cmp carCount
    bcc no_wrap
    sec
    sbc carCount
no_wrap:
    sta zCoach               ; logical coach index i

    ; carX = (BASE_X - 4 - CAR_W) - i*CAR_W
    lda #(BASE_X - 4 - Gen::CAR_W)
    ldy zCoach
    beq haveX
xsub:
    sec
    sbc #Gen::CAR_W
    dey
    bne xsub
haveX:
    sta carX

    ; cptr = OAM + CAR_BASE*4 + s*16
    txa
    asl
    asl
    asl
    asl
    clc
    adc #<(OAM + CAR_BASE * 4)
    sta cptr
    lda #>(OAM + CAR_BASE * 4)
    adc #0
    sta cptr+1

    jsr put_coach

    inx
    cpx carCount
    bne sloop
carsdone:
    rts
.endproc

; write one coach metasprite to (cptr): TL,TR,BL,BR using carX / zbTmp / zbTmp2.
.proc put_coach
    ldy #0
    lda zbTmp
    sta (cptr), y           ; TL Y
    iny
    lda #Gen::TILE_COACH00
    sta (cptr), y
    iny
    lda #3
    sta (cptr), y
    iny
    lda carX
    sta (cptr), y           ; TL X
    iny
    lda zbTmp
    sta (cptr), y           ; TR Y
    iny
    lda #Gen::TILE_COACH10
    sta (cptr), y
    iny
    lda #3
    sta (cptr), y
    iny
    lda carX
    clc
    adc #8
    sta (cptr), y           ; TR X
    iny
    lda zbTmp2
    sta (cptr), y           ; BL Y
    iny
    lda #Gen::TILE_COACH01
    sta (cptr), y
    iny
    lda #3
    sta (cptr), y
    iny
    lda carX
    sta (cptr), y           ; BL X
    iny
    lda zbTmp2
    sta (cptr), y           ; BR Y
    iny
    lda #Gen::TILE_COACH11
    sta (cptr), y
    iny
    lda #3
    sta (cptr), y
    iny
    lda carX
    clc
    adc #8
    sta (cptr), y           ; BR X
    rts
.endproc

; park a coach's four sprites off-screen.
.proc park_coach
    lda #$f0
    ldy #0
    sta (cptr), y
    ldy #4
    sta (cptr), y
    ldy #8
    sta (cptr), y
    ldy #12
    sta (cptr), y
    rts
.endproc

; ----------------------------------------------------------------------------
.proc install_body
    ldx #0
loop:
    clc
    lda rbaTrainBody + Ppu::sSprite::bPosY, x
    adc zbBaseY
    sta OAM + Ppu::sSprite::bPosY, x
    lda rbaTrainBody + Ppu::sSprite::bTile, x
    sta OAM + Ppu::sSprite::bTile, x
    lda rbaTrainBody + Ppu::sSprite::bAttr, x
    sta OAM + Ppu::sSprite::bAttr, x
    clc
    lda rbaTrainBody + Ppu::sSprite::bPosX, x
    adc #BASE_X
    sta OAM + Ppu::sSprite::bPosX, x
    inx
    inx
    inx
    inx
    cpx #(Gen::TRAIN_BODY_COUNT * 4)
    bne loop
    rts
.endproc

.proc install_wheels
    clc
    lda zbBaseY
    adc #Gen::WHEEL_DY
    sta zbWheelY

    lda spd
    beq frame0
    lda odoL
    lsr
    lsr
    and #1
    bne frame1
frame0:
    lda #Gen::TILE_WHEEL0
    jmp have_tile
frame1:
    lda #Gen::TILE_WHEEL1
have_tile:
    sta zbWTile

    ldx #0
    ldy #(WHEEL_BASE * 4)
loop:
    lda zbWheelY
    sta OAM + Ppu::sSprite::bPosY, y
    lda zbWTile
    sta OAM + Ppu::sSprite::bTile, y
    lda #1
    sta OAM + Ppu::sSprite::bAttr, y
    clc
    lda rbaWheelDX, x
    adc #BASE_X
    sta OAM + Ppu::sSprite::bPosX, y
    iny
    iny
    iny
    iny
    inx
    cpx #Gen::WHEEL_COUNT
    bne loop
    rts
.endproc

.proc install_smoke
    lda zbSmokeClock
    sta zbTmp
    ldy #(SMOKE_BASE * 4)
loop:
    lda zbTmp
    and #31
    sta zbPmask

    lda #CHIM_Y
    sec
    sbc zbPmask
    sta OAM + Ppu::sSprite::bPosY, y

    lda zbPmask
    lsr
    sta zbBaseY
    lda #CHIM_X
    sec
    sbc zbBaseY
    sta OAM + Ppu::sSprite::bPosX, y

    lda zbPmask
    cmp #4
    bcc t0
    cmp #12
    bcc t1
    cmp #22
    bcc t2
    lda #Gen::TILE_SMOKE3
    jmp settile
t0:
    lda #Gen::TILE_SMOKE0
    jmp settile
t1:
    lda #Gen::TILE_SMOKE1
    jmp settile
t2:
    lda #Gen::TILE_SMOKE2
settile:
    sta OAM + Ppu::sSprite::bTile, y
    lda #2
    sta OAM + Ppu::sSprite::bAttr, y

    lda zbTmp
    clc
    adc #6
    sta zbTmp
    iny
    iny
    iny
    iny
    cpy #(METER_BASE * 4)
    bne loop
    rts
.endproc

; 8-segment gauge: green cruise band, yellow, then red express band.
.proc install_meter
    lda spd
    lsr
    lsr
    lsr
    cmp #(Gen::METER_SEGS + 1)
    bcc store_lit
    lda #Gen::METER_SEGS
store_lit:
    sta zbLit

    ldx #0
    ldy #(METER_BASE * 4)
    lda #20
    sta zbMeterX
loop:
    lda #16
    sta OAM + Ppu::sSprite::bPosY, y
    lda zbMeterX
    sta OAM + Ppu::sSprite::bPosX, y

    cpx zbLit
    bcs seg_off
    cpx #Gen::METER_GREEN_MAX
    bcc on_green
    cpx #(Gen::METER_YELLOW_MAX + 1)
    bcc on_yellow
    lda #Gen::TILE_METER_ON3
    jmp set_on
on_yellow:
    lda #Gen::TILE_METER_ON2
    jmp set_on
on_green:
    lda #Gen::TILE_METER_ON
set_on:
    sta OAM + Ppu::sSprite::bTile, y
    lda #3
    sta OAM + Ppu::sSprite::bAttr, y
    jmp seg_next
seg_off:
    lda #Gen::TILE_METER_OFF
    sta OAM + Ppu::sSprite::bTile, y
    lda #1
    sta OAM + Ppu::sSprite::bAttr, y
seg_next:
    lda zbMeterX
    clc
    adc #8
    sta zbMeterX
    iny
    iny
    iny
    iny
    inx
    cpx #Gen::METER_SEGS
    bne loop
    rts
.endproc

; waiting passenger on the platform (only while stopped); boards before depart.
.proc install_pax
    lda mode
    bne hide
    lda dwell
    cmp #6
    bcc hide               ; boarded

    lda #(BASE_X - 12)
    sta paxX
    lda dwell
    cmp #24
    bcs no_walk
    lda #24                ; last 24 frames: shuffle toward the door
    sec
    sbc dwell
    lsr
    clc
    adc paxX
    sta paxX
no_walk:
    lda Nmi::rzbNmiCount    ; little hop
    lsr
    lsr
    lsr
    and #1
    sta zbTmp

    lda #176
    sec
    sbc zbTmp
    sta OAM + Ppu::sSprite::bPosY + (PAX_BASE * 4)
    lda #Gen::TILE_PAX0
    sta OAM + Ppu::sSprite::bTile + (PAX_BASE * 4)
    lda #0
    sta OAM + Ppu::sSprite::bAttr + (PAX_BASE * 4)
    lda paxX
    sta OAM + Ppu::sSprite::bPosX + (PAX_BASE * 4)

    lda #184
    sec
    sbc zbTmp
    sta OAM + Ppu::sSprite::bPosY + ((PAX_BASE + 1) * 4)
    lda #Gen::TILE_PAX1
    sta OAM + Ppu::sSprite::bTile + ((PAX_BASE + 1) * 4)
    lda #0
    sta OAM + Ppu::sSprite::bAttr + ((PAX_BASE + 1) * 4)
    lda paxX
    sta OAM + Ppu::sSprite::bPosX + ((PAX_BASE + 1) * 4)
    rts
hide:
    lda #$f0
    sta OAM + Ppu::sSprite::bPosY + (PAX_BASE * 4)
    sta OAM + Ppu::sSprite::bPosY + ((PAX_BASE + 1) * 4)
    rts
.endproc
