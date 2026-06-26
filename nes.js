// Minimal frame-based dual-PPU ("ANES") NES emulator, purpose-built for nanorails.
// NROM (mapper 0), two PPUs (PPU1 @ $2000-7 front, PPU2 @ $3000-7 back),
// composited PPU1-over-PPU2-over-backdrop. Frame-accurate (not cycle-accurate):
// the ROM only changes scroll/palette/OAM during vblank, so we render whole
// frames from PPU state after the NMI handler runs.

'use strict';

// ---- NES master palette (64 colours -> RGB) --------------------------------
const NES_PAL = [
  [84,84,84],[0,30,116],[8,16,144],[48,0,136],[68,0,100],[92,0,48],[84,4,0],[60,24,0],
  [32,42,0],[8,58,0],[0,64,0],[0,60,0],[0,50,60],[0,0,0],[0,0,0],[0,0,0],
  [152,150,152],[8,76,196],[48,50,236],[92,30,228],[136,20,176],[160,20,100],[152,34,32],[120,60,0],
  [84,90,0],[40,114,0],[8,124,0],[0,118,40],[0,102,120],[0,0,0],[0,0,0],[0,0,0],
  [236,238,236],[76,154,236],[120,124,236],[176,98,236],[228,84,236],[236,88,180],[236,106,100],[212,136,32],
  [160,170,0],[116,196,0],[76,208,32],[56,204,108],[56,180,204],[60,60,60],[0,0,0],[0,0,0],
  [236,238,236],[168,204,236],[188,188,236],[212,178,236],[236,174,236],[236,174,212],[236,180,176],[228,196,144],
  [204,210,120],[180,222,120],[168,226,144],[152,226,180],[160,214,228],[160,162,160],[0,0,0],[0,0,0]
];

// =============================================================================
// PPU (one instance per layer)
// =============================================================================
class PPU {
  constructor(chr, chrWritable) {
    this.chr = chr;                 // 8KB pattern memory (ROM for ppu1, RAM for ppu2)
    this.chrWritable = chrWritable;
    this.nt = new Uint8Array(0x800);   // 2KB nametable RAM (vertical mirroring)
    this.pal = new Uint8Array(32);     // palette RAM
    this.oam = new Uint8Array(256);
    this.ctrl = 0; this.mask = 0; this.status = 0;
    this.oamAddr = 0;
    this.scrollX = 0; this.scrollY = 0;
    this.vaddr = 0;                 // $2006 pointer
    this.w = 0;                     // write toggle for $2005/$2006
    this.scrollLatch = 0;           // write toggle for $2005
    this.readBuf = 0;
    // output buffers for the frame
    this.color = new Uint8Array(256 * 240);   // NES palette index per pixel
    this.opaque = new Uint8Array(256 * 240);  // 1 if this layer drew non-backdrop
  }

  // vertical mirroring: $2000/$2800 -> nt0, $2400/$2C00 -> nt1
  ntIndex(addr) {
    addr &= 0x0FFF;
    return (addr < 0x400 || (addr >= 0x800 && addr < 0xC00)) ? (addr & 0x3FF)
                                                             : 0x400 + (addr & 0x3FF);
  }
  vramRead(addr) {
    addr &= 0x3FFF;
    if (addr < 0x2000) return this.chr[addr];
    if (addr < 0x3F00) return this.nt[this.ntIndex(addr)];
    let p = addr & 0x1F; if ((p & 0x13) === 0x10) p &= ~0x10;
    return this.pal[p];
  }
  vramWrite(addr, v) {
    addr &= 0x3FFF;
    if (addr < 0x2000) { if (this.chrWritable) this.chr[addr] = v; return; }
    if (addr < 0x3F00) { this.nt[this.ntIndex(addr)] = v; return; }
    let p = addr & 0x1F; if ((p & 0x13) === 0x10) p &= ~0x10;
    this.pal[p] = v;
  }

  writeReg(r, v) {
    switch (r & 7) {
      case 0: this.ctrl = v; break;
      case 1: this.mask = v; break;
      case 3: this.oamAddr = v; break;
      case 4: this.oam[this.oamAddr++ & 0xFF] = v; break;
      case 5:
        if (this.scrollLatch === 0) { this.scrollX = v; this.scrollLatch = 1; }
        else { this.scrollY = v; this.scrollLatch = 0; }
        break;
      case 6:
        if (this.w === 0) { this.vaddr = (this.vaddr & 0x00FF) | (v << 8); this.w = 1; }
        else { this.vaddr = (this.vaddr & 0xFF00) | v; this.w = 0; }
        break;
      case 7:
        this.vramWrite(this.vaddr, v);
        this.vaddr = (this.vaddr + ((this.ctrl & 4) ? 32 : 1)) & 0x3FFF;
        break;
    }
  }
  readReg(r) {
    switch (r & 7) {
      case 2: {
        const s = this.status;
        this.status &= ~0x80;       // reading clears vblank
        this.w = 0; this.scrollLatch = 0;
        return s;
      }
      case 4: return this.oam[this.oamAddr & 0xFF];
      case 7: {
        const a = this.vaddr & 0x3FFF;
        let ret;
        if (a >= 0x3F00) { ret = this.vramRead(a); this.readBuf = this.vramRead(a - 0x1000); }
        else { ret = this.readBuf; this.readBuf = this.vramRead(a); }
        this.vaddr = (a + ((this.ctrl & 4) ? 32 : 1)) & 0x3FFF;
        return ret;
      }
    }
    return 0;
  }

  renderFrame() {
    const col = this.color, op = this.opaque;
    const bgPT = (this.ctrl & 0x10) ? 0x1000 : 0x0000;
    const sprPT = (this.ctrl & 0x08) ? 0x1000 : 0x0000;
    const baseX = (this.ctrl & 1) * 256;
    const baseY = (this.ctrl & 2) ? 240 : 0;
    const showBg = this.mask & 0x08, showSpr = this.mask & 0x10;
    const backdrop = this.pal[0];

    // ---- background ----
    for (let y = 0; y < 240; y++) {
      const sy = (baseY + this.scrollY + y) % 480;
      const ntRow = (sy >= 240) ? 1 : 0;       // (mirrored, but track for tile fetch)
      const py = sy % 240;
      const tileRow = py >> 3, fineY = py & 7;
      for (let x = 0; x < 256; x++) {
        let cidx = backdrop, opaque = 0;
        if (showBg) {
          const sx = (baseX + this.scrollX + x) & 0x1FF;   // 512px wrap
          const ntCol = (sx >= 256) ? 1 : 0;
          const px = sx & 0xFF;
          const tileCol = px >> 3, fineX = px & 7;
          // nametable select: vertical mirroring -> horizontal pair by ntCol
          const ntBase = (ntCol ? 0x400 : 0) + (ntRow ? 0 : 0); // vertical mirror folds rows
          const ntAddr = ntBase + tileRow * 32 + tileCol;
          const tile = this.nt[ntAddr & 0x7FF];
          const pAddr = bgPT + tile * 16 + fineY;
          const lo = this.chr[pAddr], hi = this.chr[pAddr + 8];
          const b = 7 - fineX;
          const c = ((lo >> b) & 1) | (((hi >> b) & 1) << 1);
          if (c) {
            // attribute
            const atAddr = ntBase + 0x3C0 + (tileRow >> 2) * 8 + (tileCol >> 2);
            const at = this.nt[atAddr & 0x7FF];
            const shift = ((tileRow & 2) << 1) | (tileCol & 2);
            const palSel = (at >> shift) & 3;
            cidx = this.pal[palSel * 4 + c];
            opaque = 1;
          }
        }
        col[y * 256 + x] = cidx;
        op[y * 256 + x] = opaque;
      }
    }

    // ---- sprites (8x8 only; render all, no per-line cap for a clean demo) ----
    if (showSpr) {
      for (let i = 63; i >= 0; i--) {       // lower index = higher priority -> draw last
        const sy = this.oam[i * 4] + 1;
        const tile = this.oam[i * 4 + 1];
        const at = this.oam[i * 4 + 2];
        const sx = this.oam[i * 4 + 3];
        if (sy >= 240 || sy <= 0) continue;
        const flipH = at & 0x40, flipV = at & 0x80;
        const palBase = 0x10 + (at & 3) * 4;
        const behind = at & 0x20;
        for (let r = 0; r < 8; r++) {
          const py = sy + r; if (py < 0 || py >= 240) continue;
          const ry = flipV ? 7 - r : r;
          const pAddr = sprPT + tile * 16 + ry;
          const lo = this.chr[pAddr], hi = this.chr[pAddr + 8];
          for (let c = 0; c < 8; c++) {
            const px = sx + c; if (px < 0 || px >= 256) continue;
            const cx = flipH ? c : 7 - c;
            const v = ((lo >> cx) & 1) | (((hi >> cx) & 1) << 1);
            if (!v) continue;
            const idx = py * 256 + px;
            if (behind && op[idx]) continue;   // behind opaque bg
            col[idx] = this.pal[palBase + v];
            op[idx] = 1;
          }
        }
      }
    }
  }
}

// =============================================================================
// APU — pulse1, pulse2, noise (what nanorails' SFX use). Synthesised on demand
// from live register state; the ROM manages envelopes each frame.
// =============================================================================
const CPU_HZ = 1789773;
const NOISE_PERIODS = [4,8,16,32,64,96,128,160,202,254,380,508,762,1016,2034,4068];
const DUTY = [0.125, 0.25, 0.5, 0.75];

class APU {
  constructor() {
    this.reg = new Uint8Array(0x18);
    this.enable = 0;
    this.sampleRate = 44100;
    this.p1ph = 0; this.p2ph = 0;
    this.lfsr = 1; this.nAcc = 0;
  }
  write(a, v) {
    a &= 0x1F;
    this.reg[a] = v;
    if (a === 0x15) this.enable = v;
  }
  pulse(i, ph) {
    const o = i * 4;
    const r0 = this.reg[o], r2 = this.reg[o + 2], r3 = this.reg[o + 3];
    if (!(this.enable & (1 << i))) return 0;
    const period = r2 | ((r3 & 7) << 8);
    if (period < 8) return 0;
    const vol = (r0 & 0x10) ? (r0 & 0x0F) : (r0 & 0x0F); // ROM uses constant volume
    if (!vol) return 0;
    const duty = DUTY[(r0 >> 6) & 3];
    return ((ph % 1) < duty ? 1 : -1) * (vol / 15);
  }
  freq(i) {
    const o = i * 4;
    const period = this.reg[o + 2] | ((this.reg[o + 3] & 7) << 8);
    return CPU_HZ / (16 * (period + 1));
  }
  render(buf) {
    const n = buf.length, sr = this.sampleRate;
    const f1 = this.freq(0) / sr, f2 = this.freq(1) / sr;
    const nEnable = this.enable & 8;
    const nVol = (this.reg[0x0C] & 0x0F) / 15;
    const nPeriod = NOISE_PERIODS[this.reg[0x0E] & 0x0F];
    const nStep = CPU_HZ / nPeriod / sr;     // LFSR shifts per output sample
    for (let s = 0; s < n; s++) {
      let v = 0;
      v += this.pulse(0, this.p1ph) * 0.16;
      v += this.pulse(1, this.p2ph) * 0.16;
      if (nEnable && nVol) {
        this.nAcc += nStep;
        while (this.nAcc >= 1) {
          this.nAcc -= 1;
          const fb = (this.lfsr ^ (this.lfsr >> 1)) & 1;
          this.lfsr = (this.lfsr >> 1) | (fb << 14);
        }
        v += ((this.lfsr & 1) ? 1 : -1) * nVol * 0.12;
      }
      this.p1ph += f1; if (this.p1ph > 1e6) this.p1ph = 0;
      this.p2ph += f2; if (this.p2ph > 1e6) this.p2ph = 0;
      buf[s] = v > 1 ? 1 : v < -1 ? -1 : v;
    }
  }
}

// =============================================================================
// NES machine: CPU + bus + 2 PPUs
// =============================================================================
class NES {
  constructor(romBytes) {
    this.loadRom(romBytes);
    this.ram = new Uint8Array(0x800);
    this.ppu1 = new PPU(this.chrRom, false);             // front, CHR-ROM
    this.ppu2 = new PPU(new Uint8Array(0x2000), true);   // back, CHR-RAM
    this.pad = 0; this.padShift = 0; this.strobe = 0;
    this.apu = new APU();
    this.out = new Uint8ClampedArray(256 * 240 * 4);
    this.initCPU();
  }

  loadRom(b) {
    if (b[0] !== 0x4E || b[1] !== 0x45 || b[2] !== 0x53) throw new Error('not iNES');
    const prg = b[4], chr = b[5];
    let off = 16 + ((b[6] & 4) ? 512 : 0);
    this.prgRom = b.slice(off, off + prg * 0x4000); off += prg * 0x4000;
    this.chrRom = chr ? b.slice(off, off + chr * 0x2000) : new Uint8Array(0x2000);
    this.prg16 = prg === 1;   // mirror if single 16K bank
  }

  // ---- bus ----
  read(a) {
    a &= 0xFFFF;
    if (a < 0x2000) return this.ram[a & 0x7FF];
    if (a < 0x3000) return this.ppu1.readReg(a);
    if (a < 0x3008) return this.ppu2.readReg(a);
    if (a < 0x4000) return this.ppu1.readReg(a);   // $3008-3FFF mirror PPU1 (unused)
    if (a === 0x4016) {
      const v = this.padShift & 1; this.padShift >>= 1; return v | 0x40;
    }
    if (a === 0x4017) return 0x40;
    if (a >= 0x8000) {
      let o = a - 0x8000; if (this.prg16) o &= 0x3FFF;
      return this.prgRom[o];
    }
    return 0;
  }
  write(a, v) {
    a &= 0xFFFF; v &= 0xFF;
    if (a < 0x2000) { this.ram[a & 0x7FF] = v; return; }
    if (a < 0x3000) { this.ppu1.writeReg(a, v); return; }
    if (a < 0x3008) { this.ppu2.writeReg(a, v); return; }
    if (a < 0x4000) { this.ppu1.writeReg(a, v); return; }
    if (a === 0x4014) {                 // OAM DMA -> PPU1
      const base = v << 8;
      for (let i = 0; i < 256; i++) this.ppu1.oam[(this.ppu1.oamAddr + i) & 0xFF] = this.read(base + i);
      this.cyc += 513; return;
    }
    if (a === 0x4016) {
      this.strobe = v & 1;
      if (this.strobe) this.padShift = this.pad;
      return;
    }
    if ((a >= 0x4000 && a <= 0x4013) || a === 0x4015 || a === 0x4017) {
      this.apu.write(a, v);
    }
  }

  // ---- 6502 ----
  initCPU() {
    this.A = 0; this.X = 0; this.Y = 0; this.S = 0xFD;
    this.PC = this.read16(0xFFFC);
    this.C = 0; this.Z = 0; this.I = 1; this.D = 0; this.V = 0; this.N = 0;
    this.cyc = 0;
  }
  read16(a) { return this.read(a) | (this.read((a & 0xFF00) | ((a + 1) & 0xFF)) | 0) << 8; }
  read16w(a) { return this.read(a) | (this.read((a + 1) & 0xFFFF) << 8); }
  getP(brk) {
    return (this.C) | (this.Z << 1) | (this.I << 2) | (this.D << 3) |
           (brk << 4) | (1 << 5) | (this.V << 6) | (this.N << 7);
  }
  setP(p) {
    this.C = p & 1; this.Z = (p >> 1) & 1; this.I = (p >> 2) & 1; this.D = (p >> 3) & 1;
    this.V = (p >> 6) & 1; this.N = (p >> 7) & 1;
  }
  push(v) { this.write(0x100 + this.S, v & 0xFF); this.S = (this.S - 1) & 0xFF; }
  pop() { this.S = (this.S + 1) & 0xFF; return this.read(0x100 + this.S); }
  setZN(v) { this.Z = (v & 0xFF) === 0 ? 1 : 0; this.N = (v >> 7) & 1; }

  nmi() {
    this.push(this.PC >> 8); this.push(this.PC & 0xFF); this.push(this.getP(0));
    this.I = 1; this.PC = this.read16(0xFFFA); this.cyc += 7;
  }

  step() {
    const op = this.read(this.PC); this.PC = (this.PC + 1) & 0xFFFF;
    let addr = 0, m, t;
    const imm = () => { const a = this.PC; this.PC = (this.PC + 1) & 0xFFFF; return a; };
    const zp = () => this.read(imm());
    const zpx = () => (this.read(imm()) + this.X) & 0xFF;
    const zpy = () => (this.read(imm()) + this.Y) & 0xFF;
    const ab = () => { const a = this.read16w(this.PC); this.PC = (this.PC + 2) & 0xFFFF; return a; };
    const abx = () => (ab() + this.X) & 0xFFFF;
    const aby = () => (ab() + this.Y) & 0xFFFF;
    const inx = () => { const z = (this.read(imm()) + this.X) & 0xFF; return this.read(z) | (this.read((z + 1) & 0xFF) << 8); };
    const iny = () => { const z = this.read(imm()); return ((this.read(z) | (this.read((z + 1) & 0xFF) << 8)) + this.Y) & 0xFFFF; };

    const ld = (a) => this.read(a);
    const branch = (c) => { const o = this.read(imm()); if (c) { this.PC = (this.PC + ((o < 0x80) ? o : o - 256)) & 0xFFFF; this.cyc += 1; } };
    const cmp = (r, v) => { const d = r - v; this.C = d >= 0 ? 1 : 0; this.setZN(d & 0xFF); };
    const ADC = (v) => { const s = this.A + v + this.C; this.V = (~(this.A ^ v) & (this.A ^ s) & 0x80) ? 1 : 0; this.C = s > 0xFF ? 1 : 0; this.A = s & 0xFF; this.setZN(this.A); };
    const SBC = (v) => ADC(v ^ 0xFF);

    this.cyc += 2;
    switch (op) {
      // loads
      case 0xA9: this.A = ld(imm()); this.setZN(this.A); break;
      case 0xA5: this.A = ld(zp()); this.setZN(this.A); break;
      case 0xB5: this.A = ld(zpx()); this.setZN(this.A); break;
      case 0xAD: this.A = ld(ab()); this.setZN(this.A); break;
      case 0xBD: this.A = ld(abx()); this.setZN(this.A); break;
      case 0xB9: this.A = ld(aby()); this.setZN(this.A); break;
      case 0xA1: this.A = ld(inx()); this.setZN(this.A); break;
      case 0xB1: this.A = ld(iny()); this.setZN(this.A); break;
      case 0xA2: this.X = ld(imm()); this.setZN(this.X); break;
      case 0xA6: this.X = ld(zp()); this.setZN(this.X); break;
      case 0xB6: this.X = ld(zpy()); this.setZN(this.X); break;
      case 0xAE: this.X = ld(ab()); this.setZN(this.X); break;
      case 0xBE: this.X = ld(aby()); this.setZN(this.X); break;
      case 0xA0: this.Y = ld(imm()); this.setZN(this.Y); break;
      case 0xA4: this.Y = ld(zp()); this.setZN(this.Y); break;
      case 0xB4: this.Y = ld(zpx()); this.setZN(this.Y); break;
      case 0xAC: this.Y = ld(ab()); this.setZN(this.Y); break;
      case 0xBC: this.Y = ld(abx()); this.setZN(this.Y); break;
      // stores
      case 0x85: this.write(zp(), this.A); break;
      case 0x95: this.write(zpx(), this.A); break;
      case 0x8D: this.write(ab(), this.A); break;
      case 0x9D: this.write(abx(), this.A); break;
      case 0x99: this.write(aby(), this.A); break;
      case 0x81: this.write(inx(), this.A); break;
      case 0x91: this.write(iny(), this.A); break;
      case 0x86: this.write(zp(), this.X); break;
      case 0x96: this.write(zpy(), this.X); break;
      case 0x8E: this.write(ab(), this.X); break;
      case 0x84: this.write(zp(), this.Y); break;
      case 0x94: this.write(zpx(), this.Y); break;
      case 0x8C: this.write(ab(), this.Y); break;
      // transfers
      case 0xAA: this.X = this.A; this.setZN(this.X); break;
      case 0xA8: this.Y = this.A; this.setZN(this.Y); break;
      case 0x8A: this.A = this.X; this.setZN(this.A); break;
      case 0x98: this.A = this.Y; this.setZN(this.A); break;
      case 0xBA: this.X = this.S; this.setZN(this.X); break;
      case 0x9A: this.S = this.X; break;
      // stack
      case 0x48: this.push(this.A); break;
      case 0x68: this.A = this.pop(); this.setZN(this.A); break;
      case 0x08: this.push(this.getP(1)); break;
      case 0x28: this.setP(this.pop()); break;
      // logic
      case 0x29: this.A &= ld(imm()); this.setZN(this.A); break;
      case 0x25: this.A &= ld(zp()); this.setZN(this.A); break;
      case 0x35: this.A &= ld(zpx()); this.setZN(this.A); break;
      case 0x2D: this.A &= ld(ab()); this.setZN(this.A); break;
      case 0x3D: this.A &= ld(abx()); this.setZN(this.A); break;
      case 0x39: this.A &= ld(aby()); this.setZN(this.A); break;
      case 0x21: this.A &= ld(inx()); this.setZN(this.A); break;
      case 0x31: this.A &= ld(iny()); this.setZN(this.A); break;
      case 0x09: this.A |= ld(imm()); this.setZN(this.A); break;
      case 0x05: this.A |= ld(zp()); this.setZN(this.A); break;
      case 0x15: this.A |= ld(zpx()); this.setZN(this.A); break;
      case 0x0D: this.A |= ld(ab()); this.setZN(this.A); break;
      case 0x1D: this.A |= ld(abx()); this.setZN(this.A); break;
      case 0x19: this.A |= ld(aby()); this.setZN(this.A); break;
      case 0x01: this.A |= ld(inx()); this.setZN(this.A); break;
      case 0x11: this.A |= ld(iny()); this.setZN(this.A); break;
      case 0x49: this.A ^= ld(imm()); this.setZN(this.A); break;
      case 0x45: this.A ^= ld(zp()); this.setZN(this.A); break;
      case 0x55: this.A ^= ld(zpx()); this.setZN(this.A); break;
      case 0x4D: this.A ^= ld(ab()); this.setZN(this.A); break;
      case 0x5D: this.A ^= ld(abx()); this.setZN(this.A); break;
      case 0x59: this.A ^= ld(aby()); this.setZN(this.A); break;
      case 0x41: this.A ^= ld(inx()); this.setZN(this.A); break;
      case 0x51: this.A ^= ld(iny()); this.setZN(this.A); break;
      // bit
      case 0x24: m = ld(zp()); this.Z = (this.A & m) === 0 ? 1 : 0; this.V = (m >> 6) & 1; this.N = (m >> 7) & 1; break;
      case 0x2C: m = ld(ab()); this.Z = (this.A & m) === 0 ? 1 : 0; this.V = (m >> 6) & 1; this.N = (m >> 7) & 1; break;
      // compare
      case 0xC9: cmp(this.A, ld(imm())); break;
      case 0xC5: cmp(this.A, ld(zp())); break;
      case 0xD5: cmp(this.A, ld(zpx())); break;
      case 0xCD: cmp(this.A, ld(ab())); break;
      case 0xDD: cmp(this.A, ld(abx())); break;
      case 0xD9: cmp(this.A, ld(aby())); break;
      case 0xC1: cmp(this.A, ld(inx())); break;
      case 0xD1: cmp(this.A, ld(iny())); break;
      case 0xE0: cmp(this.X, ld(imm())); break;
      case 0xE4: cmp(this.X, ld(zp())); break;
      case 0xEC: cmp(this.X, ld(ab())); break;
      case 0xC0: cmp(this.Y, ld(imm())); break;
      case 0xC4: cmp(this.Y, ld(zp())); break;
      case 0xCC: cmp(this.Y, ld(ab())); break;
      // arithmetic
      case 0x69: ADC(ld(imm())); break;
      case 0x65: ADC(ld(zp())); break;
      case 0x75: ADC(ld(zpx())); break;
      case 0x6D: ADC(ld(ab())); break;
      case 0x7D: ADC(ld(abx())); break;
      case 0x79: ADC(ld(aby())); break;
      case 0x61: ADC(ld(inx())); break;
      case 0x71: ADC(ld(iny())); break;
      case 0xE9: SBC(ld(imm())); break;
      case 0xE5: SBC(ld(zp())); break;
      case 0xF5: SBC(ld(zpx())); break;
      case 0xED: SBC(ld(ab())); break;
      case 0xFD: SBC(ld(abx())); break;
      case 0xF9: SBC(ld(aby())); break;
      case 0xE1: SBC(ld(inx())); break;
      case 0xF1: SBC(ld(iny())); break;
      // inc/dec
      case 0xE6: addr = zp(); m = (ld(addr) + 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xF6: addr = zpx(); m = (ld(addr) + 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xEE: addr = ab(); m = (ld(addr) + 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xFE: addr = abx(); m = (ld(addr) + 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xC6: addr = zp(); m = (ld(addr) - 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xD6: addr = zpx(); m = (ld(addr) - 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xCE: addr = ab(); m = (ld(addr) - 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xDE: addr = abx(); m = (ld(addr) - 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0xE8: this.X = (this.X + 1) & 0xFF; this.setZN(this.X); break;
      case 0xC8: this.Y = (this.Y + 1) & 0xFF; this.setZN(this.Y); break;
      case 0xCA: this.X = (this.X - 1) & 0xFF; this.setZN(this.X); break;
      case 0x88: this.Y = (this.Y - 1) & 0xFF; this.setZN(this.Y); break;
      // shifts
      case 0x0A: this.C = (this.A >> 7) & 1; this.A = (this.A << 1) & 0xFF; this.setZN(this.A); break;
      case 0x06: addr = zp(); m = ld(addr); this.C = (m >> 7) & 1; m = (m << 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x16: addr = zpx(); m = ld(addr); this.C = (m >> 7) & 1; m = (m << 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x0E: addr = ab(); m = ld(addr); this.C = (m >> 7) & 1; m = (m << 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x1E: addr = abx(); m = ld(addr); this.C = (m >> 7) & 1; m = (m << 1) & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x4A: this.C = this.A & 1; this.A >>= 1; this.setZN(this.A); break;
      case 0x46: addr = zp(); m = ld(addr); this.C = m & 1; m >>= 1; this.write(addr, m); this.setZN(m); break;
      case 0x56: addr = zpx(); m = ld(addr); this.C = m & 1; m >>= 1; this.write(addr, m); this.setZN(m); break;
      case 0x4E: addr = ab(); m = ld(addr); this.C = m & 1; m >>= 1; this.write(addr, m); this.setZN(m); break;
      case 0x5E: addr = abx(); m = ld(addr); this.C = m & 1; m >>= 1; this.write(addr, m); this.setZN(m); break;
      case 0x2A: t = (this.A << 1) | this.C; this.C = (this.A >> 7) & 1; this.A = t & 0xFF; this.setZN(this.A); break;
      case 0x26: addr = zp(); m = ld(addr); t = (m << 1) | this.C; this.C = (m >> 7) & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x36: addr = zpx(); m = ld(addr); t = (m << 1) | this.C; this.C = (m >> 7) & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x2E: addr = ab(); m = ld(addr); t = (m << 1) | this.C; this.C = (m >> 7) & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x3E: addr = abx(); m = ld(addr); t = (m << 1) | this.C; this.C = (m >> 7) & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x6A: t = (this.A >> 1) | (this.C << 7); this.C = this.A & 1; this.A = t & 0xFF; this.setZN(this.A); break;
      case 0x66: addr = zp(); m = ld(addr); t = (m >> 1) | (this.C << 7); this.C = m & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x76: addr = zpx(); m = ld(addr); t = (m >> 1) | (this.C << 7); this.C = m & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x6E: addr = ab(); m = ld(addr); t = (m >> 1) | (this.C << 7); this.C = m & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      case 0x7E: addr = abx(); m = ld(addr); t = (m >> 1) | (this.C << 7); this.C = m & 1; m = t & 0xFF; this.write(addr, m); this.setZN(m); break;
      // jumps / calls
      case 0x4C: this.PC = ab(); break;
      case 0x6C: addr = ab(); this.PC = this.read(addr) | (this.read((addr & 0xFF00) | ((addr + 1) & 0xFF)) << 8); break;
      case 0x20: addr = ab(); { const r = (this.PC - 1) & 0xFFFF; this.push(r >> 8); this.push(r & 0xFF); } this.PC = addr; break;
      case 0x60: { const lo = this.pop(), hi = this.pop(); this.PC = ((lo | (hi << 8)) + 1) & 0xFFFF; } break;
      case 0x40: this.setP(this.pop()); { const lo = this.pop(), hi = this.pop(); this.PC = lo | (hi << 8); } break;
      // branches
      case 0x10: branch(!this.N); break;
      case 0x30: branch(this.N); break;
      case 0x50: branch(!this.V); break;
      case 0x70: branch(this.V); break;
      case 0x90: branch(!this.C); break;
      case 0xB0: branch(this.C); break;
      case 0xD0: branch(!this.Z); break;
      case 0xF0: branch(this.Z); break;
      // flags
      case 0x18: this.C = 0; break;
      case 0x38: this.C = 1; break;
      case 0x58: this.I = 0; break;
      case 0x78: this.I = 1; break;
      case 0xB8: this.V = 0; break;
      case 0xD8: this.D = 0; break;
      case 0xF8: this.D = 1; break;
      // nop / brk
      case 0xEA: break;
      case 0x00: this.PC = (this.PC + 1) & 0xFFFF; break; // treat BRK as nop-ish (unused)
      default: break; // unknown/illegal: skip
    }
  }

  runFrame() {
    this.ppu1.status |= 0x80; this.ppu2.status |= 0x80;
    if (this.ppu1.ctrl & 0x80) this.nmi();
    const target = this.cyc + 29780;
    let guard = 400000;
    while (this.cyc < target && guard-- > 0) this.step();
    this.ppu1.status &= ~0x80; this.ppu2.status &= ~0x80;
    this.render();
  }

  render() {
    this.ppu1.renderFrame();
    this.ppu2.renderFrame();
    const c1 = this.ppu1.color, o1 = this.ppu1.opaque;
    const c2 = this.ppu2.color, o2 = this.ppu2.opaque;
    const bd = this.ppu1.pal[0];
    const out = this.out;
    for (let i = 0; i < 256 * 240; i++) {
      let nesc;
      if (o1[i]) nesc = c1[i];
      else if (o2[i]) nesc = c2[i];
      else nesc = bd;
      const rgb = NES_PAL[nesc & 0x3F];
      const j = i * 4;
      out[j] = rgb[0]; out[j + 1] = rgb[1]; out[j + 2] = rgb[2]; out[j + 3] = 255;
    }
  }

  setButton(bit, down) {
    if (down) this.pad |= (1 << bit); else this.pad &= ~(1 << bit);
  }
}

if (typeof module !== 'undefined') module.exports = { NES };
