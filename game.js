/* nanorails — game shell / meta-game wrapper
 * Wraps the dual-PPU NES emulator (global `NES`) with a title screen, pause
 * menu, localStorage save system, HUD (money / fuel / inventory / route map),
 * and a simple economy + shop.
 *
 * Live emulator state is read via machine.peekRAM(addr) (guarded):
 *   0x700 mode (0=dwell, 1=running)
 *   0x701 carCount (0..5)
 *   0x702/0x703 odometer lo/hi (16-bit, px, wraps at 65536)
 *   0x704 spd (0..~72, 1/16 px per frame)
 *   0x705 arrivals (++ per station arrival, wraps at 256)
 */
(function () {
  'use strict';

  // ---------- constants / tuning ----------
  const SAVE_KEY = 'nanorails.save';
  // Fuel burn per odometer pixel. A leg is LEG_LEN px; tuned so a full default
  // tank (1000) lasts a handful of legs.
  const FUEL_RATE = 0.012;
  const LEG_LEN = 85 * 256;          // nominal trip distance in px
  const ECON_BASE = 10;              // money per arrival
  const ECON_PER_CAR = 8;            // extra per coupled coach
  const HUD_HZ = 10;                 // DOM refresh cap (per second)

  const DEFAULTS = {
    money: 50,
    fuel: 1000,
    maxFuel: 1000,
    upgrades: {},                    // { tankLvl: n, ... }
    settings: { muted: false, volume: 1 }
  };

  const TANK_STEP = 500;             // maxFuel added per tank upgrade
  const TANK_BASE_COST = 120;        // first tank upgrade cost
  const TANK_COST_GROWTH = 90;       // added per level already owned
  const REFUEL_PER_UNIT = 0.05;      // money per fuel unit when refueling

  // ---------- safe RAM peek ----------
  function peek(machine, a) {
    return (machine && machine.peekRAM) ? (machine.peekRAM(a) | 0) : 0;
  }

  // ---------- save system ----------
  function loadSave() {
    let s;
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (raw) s = JSON.parse(raw);
    } catch (e) { /* corrupt save -> defaults */ }
    return normalizeSave(s);
  }

  function normalizeSave(s) {
    s = s && typeof s === 'object' ? s : {};
    const out = {
      money: Number.isFinite(s.money) ? s.money : DEFAULTS.money,
      maxFuel: Number.isFinite(s.maxFuel) ? s.maxFuel : DEFAULTS.maxFuel,
      fuel: Number.isFinite(s.fuel) ? s.fuel : DEFAULTS.fuel,
      upgrades: (s.upgrades && typeof s.upgrades === 'object') ? s.upgrades : {},
      settings: {
        muted: !!(s.settings && s.settings.muted),
        volume: (s.settings && Number.isFinite(s.settings.volume)) ? s.settings.volume : 1
      }
    };
    out.fuel = Math.max(0, Math.min(out.fuel, out.maxFuel));
    return out;
  }

  function defaultSave() {
    return normalizeSave(JSON.parse(JSON.stringify(DEFAULTS)));
  }

  // ---------- Game ----------
  function Game(opts) {
    this.el = opts.el;                 // map of named DOM elements
    this.onAudioVolume = opts.onAudioVolume || function () {};
    this.save = loadSave();

    // live (non-persisted) runtime state
    this.carCount = 0;
    this.mode = 0;
    this.spd = 0;
    this.legProgress = 0;              // px into current leg
    this.outOfFuel = false;

    // delta trackers
    this._lastOdo = null;             // 16-bit odometer last seen
    this._lastArrivals = null;        // arrivals counter last seen
    this._started = false;

    // throttle
    this._hudAccum = 0;
    this._hudInterval = 1000 / HUD_HZ;
    this._lastHudT = 0;

    this._dirty = false;              // save needs flushing
  }

  Game.prototype.markStarted = function () { this._started = true; };

  // Read 16-bit odometer and return delta since last call, handling wrap.
  Game.prototype._odoDelta = function (machine) {
    const lo = peek(machine, 0x702);
    const hi = peek(machine, 0x703);
    const odo = (hi << 8) | lo;
    if (this._lastOdo === null) { this._lastOdo = odo; return 0; }
    let d = odo - this._lastOdo;
    if (d < 0) d += 65536;            // wrapped
    // ignore absurd jumps (e.g. ROM reset) to avoid nuking fuel
    if (d > 4096) d = 0;
    this._lastOdo = odo;
    return d;
  };

  // Called once per emulated frame after machine.runFrame().
  Game.prototype.tick = function (machine) {
    if (!this._started) return;

    this.mode = peek(machine, 0x700);
    this.carCount = peek(machine, 0x701);
    this.spd = peek(machine, 0x704);

    const dOdo = this._odoDelta(machine);

    // advance leg progress
    if (dOdo) {
      this.legProgress += dOdo;
      if (this.legProgress > LEG_LEN) this.legProgress = LEG_LEN;
    }

    // burn fuel as the train moves (only if we have any)
    if (dOdo && this.save.fuel > 0) {
      this.save.fuel = Math.max(0, this.save.fuel - dOdo * FUEL_RATE);
      this._dirty = true;
    }
    this.outOfFuel = this.save.fuel <= 0;

    // arrivals -> economy + reset leg
    const arr = peek(machine, 0x705);
    if (this._lastArrivals === null) {
      this._lastArrivals = arr;
    } else if (arr !== this._lastArrivals) {
      let da = arr - this._lastArrivals;
      if (da < 0) da += 256;          // wrap
      this._lastArrivals = arr;
      if (da > 0 && da < 16) {        // sanity bound
        for (let i = 0; i < da; i++) this._awardArrival();
        this.legProgress = 0;         // new leg begins
      }
    }
  };

  Game.prototype._awardArrival = function () {
    const reward = ECON_BASE + this.carCount * ECON_PER_CAR;
    this.save.money += reward;
    this._dirty = true;
  };

  // ---------- economy / shop actions ----------
  Game.prototype.refuelCost = function () {
    const missing = Math.max(0, this.save.maxFuel - this.save.fuel);
    return Math.ceil(missing * REFUEL_PER_UNIT);
  };

  Game.prototype.canRefuel = function () {
    const c = this.refuelCost();
    return c > 0 && this.save.money >= c;
  };

  Game.prototype.refuel = function () {
    const c = this.refuelCost();
    if (c <= 0 || this.save.money < c) return false;
    this.save.money -= c;
    this.save.fuel = this.save.maxFuel;
    this.outOfFuel = false;
    this._dirty = true;
    this.flush();
    return true;
  };

  Game.prototype.tankLevel = function () {
    return this.save.upgrades.tankLvl || 0;
  };

  Game.prototype.tankCost = function () {
    return TANK_BASE_COST + this.tankLevel() * TANK_COST_GROWTH;
  };

  Game.prototype.canBuyTank = function () {
    return this.save.money >= this.tankCost();
  };

  Game.prototype.buyTank = function () {
    const c = this.tankCost();
    if (this.save.money < c) return false;
    this.save.money -= c;
    this.save.upgrades.tankLvl = this.tankLevel() + 1;
    this.save.maxFuel += TANK_STEP;
    this._dirty = true;
    this.flush();
    return true;
  };

  // ---------- save flush ----------
  Game.prototype.flush = function () {
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(this.save));
      this._dirty = false;
    } catch (e) { /* storage full / disabled */ }
  };
  Game.prototype.flushIfDirty = function () { if (this._dirty) this.flush(); };

  Game.prototype.resetSave = function () {
    this.save = defaultSave();
    this.legProgress = 0;
    this.outOfFuel = false;
    this.flush();
    this.onAudioVolume(this.effectiveVolume());
  };

  // ---------- audio settings ----------
  Game.prototype.effectiveVolume = function () {
    return this.save.settings.muted ? 0 : this.save.settings.volume;
  };
  Game.prototype.toggleMute = function () {
    this.save.settings.muted = !this.save.settings.muted;
    this._dirty = true;
    this.flush();
    this.onAudioVolume(this.effectiveVolume());
    return this.save.settings.muted;
  };

  // ---------- HUD rendering (throttled) ----------
  Game.prototype.maybeRenderHud = function (now) {
    if (!this._lastHudT) this._lastHudT = now;
    if (now - this._lastHudT < this._hudInterval) return;
    this._lastHudT = now;
    this.renderHud();
  };

  Game.prototype.renderHud = function () {
    const e = this.el;

    // money
    if (e.money) e.money.textContent = '$ ' + formatInt(Math.floor(this.save.money));

    // fuel gauge
    const pct = this.save.maxFuel > 0
      ? Math.max(0, Math.min(1, this.save.fuel / this.save.maxFuel)) : 0;
    if (e.fuelBar) {
      e.fuelBar.style.width = (pct * 100).toFixed(1) + '%';
      let col = 'var(--accent)';
      if (pct < 0.5) col = '#e7d36a';
      if (pct < 0.2) col = '#e76a6a';
      e.fuelBar.style.background = col;
    }
    if (e.fuelTxt) {
      e.fuelTxt.textContent = Math.ceil(this.save.fuel) + ' / ' + this.save.maxFuel;
    }
    if (e.fuelWrap) e.fuelWrap.classList.toggle('empty', this.outOfFuel);
    if (e.outOfFuel) e.outOfFuel.style.display = this.outOfFuel ? '' : 'none';

    // inventory: coaches + upgrades
    if (e.cars) {
      const n = this.carCount;
      e.cars.textContent = '🚃 × ' + n;
    }
    if (e.upgrades) {
      const lvl = this.tankLevel();
      e.upgrades.textContent = lvl > 0 ? ('⛽ tank L' + lvl) : '—';
    }

    // route map: train marker position along the leg
    if (e.train) {
      const p = Math.max(0, Math.min(1, this.legProgress / LEG_LEN));
      e.train.style.left = (p * 100).toFixed(2) + '%';
    }
    // pulse the destination station while running
    if (e.dest) e.dest.classList.toggle('active', this.mode === 1);
    if (e.origin) e.origin.classList.toggle('active', this.mode !== 1);
  };

  // refresh shop labels/buttons
  Game.prototype.renderShop = function () {
    const e = this.el;
    if (e.shopMoney) e.shopMoney.textContent = '$ ' + formatInt(Math.floor(this.save.money));

    const rc = this.refuelCost();
    if (e.refuelBtn) {
      e.refuelBtn.disabled = !this.canRefuel();
      e.refuelBtn.querySelector('.cost').textContent =
        rc > 0 ? ('$' + rc) : 'full';
    }
    if (e.refuelDesc) {
      e.refuelDesc.textContent =
        'Top up the tank (' + Math.ceil(this.save.fuel) + '/' + this.save.maxFuel + ').';
    }

    const tc = this.tankCost();
    if (e.tankBtn) {
      e.tankBtn.disabled = !this.canBuyTank();
      e.tankBtn.querySelector('.cost').textContent = '$' + tc;
    }
    if (e.tankDesc) {
      e.tankDesc.textContent =
        'Bigger tank: +' + TANK_STEP + ' max fuel (now ' + this.save.maxFuel +
        ', L' + this.tankLevel() + ').';
    }
  };

  // ---------- helpers ----------
  function formatInt(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  // expose
  window.NanoGame = { Game: Game, loadSave: loadSave, defaultSave: defaultSave, SAVE_KEY: SAVE_KEY };
})();
