# Milestone 3 — Party Combat (2v2)

Builds on M2. The biggest structural change since M0: from 1v1 to **two heroes vs two
enemies**. Bounded hard — **single-target only**, **dumb enemy AI**. Everything from
M0–M2 stays unless stated. Combatants are still simple shapes (sprites are a later
milestone); all drawing still goes through the M2 `draw_combatant` function, now
called once per combatant.

## Stack
- Unchanged. Python 3.11+, pygame, no new dependencies, no asset files.

## What's new
1. **Two parties.** 2 heroes on one side, 2 enemies on the other, laid out so all four
   are visible with their HP/MP/ATB. Each combatant keeps its own independent ATB bar.
2. **Target selection.** When a hero uses a single-target action (Attack or Fire), the
   player picks a **target among living enemies** via a cursor (highlight the current
   target; left/right or up/down to switch; confirm to act; back to cancel without
   spending the turn). Default the cursor to the first living enemy. Dead enemies are
   not selectable.
3. **Turn arbitration.** More than one hero bar can fill. Resolve **one hero's menu at
   a time, in the order their bars filled** (FIFO). A hero whose bar is full while
   another hero is acting/choosing **waits with a full bar** (does not overflow or get
   skipped). Consistent with M2: while any action animates or a hero menu is open, **all
   ATB filling is paused** and input belongs to the active hero only.
4. **Enemy AI (deliberately dumb).** On a full bar, an enemy attacks a **random living
   hero**, single target. No targeting smarts, no coordination.
5. **Win / lose.** Win when **all enemies** are defeated; lose when **all heroes** are
   defeated. A defeated combatant plays the M2 death fade and is removed from play and
   from targeting.

## Stats
| | HP | MP | attack | defense | speed |
|---|---|---|---|---|---|
| Hero 1 | 100 | 30 | 20 | 5 | 12 |
| Hero 2 | 70 | 50 | 12 | 3 | 14 |
| Enemy 1 | 60 | — | 12 | 3 | 9 |
| Enemy 2 | 50 | — | 10 | 2 | 11 |

Both heroes share the same action set (`Attack` / `Magic` → `Fire`); **Fire** is
unchanged (power 25, 10 MP, ignores defense). Per-character unique abilities are NOT
in scope.

## Edge cases to handle
- Target cursor only ever lands on living enemies; if the current target dies, snap to
  another living one.
- If a side is wiped mid-turn, end the battle immediately (don't finish a queued menu).
- A hero with a full bar waiting in the queue must not be lost if another combatant
  dies or acts in the meantime.

## Done criteria
- [ ] Four combatants (2 heroes, 2 enemies) shown with HP/MP/ATB.
- [ ] Hero single-target actions prompt a target cursor over living enemies; cancel
      returns to the menu without spending the turn.
- [ ] Two hero bars filling are resolved one at a time in fill order; a waiting hero
      keeps its full bar.
- [ ] Enemies attack a random living hero on a full bar.
- [ ] Win requires all enemies defeated; lose requires all heroes defeated.
- [ ] Dead combatants fade out and leave targeting/turn rotation.
- [ ] ATB pauses during any menu/action; no input leaks to non-active combatants; no
      crashes across a win and a loss.

## Explicitly DEFERRED — out of scope for M3
Sprites / image assets · sound · area-of-effect / multi-target actions · smarter enemy
AI · per-character unique abilities · variable party size (>2) · rows/positioning ·
turn-order display · items · multiple spells · elemental weaknesses · status effects ·
levels/XP/equipment · overworld · tile maps · NPCs · dialogue · save/load.
