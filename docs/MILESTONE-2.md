# Milestone 2 — Game Feel ("juice")

Builds on M1. **No new art assets** — combatants stay as simple shapes. This milestone
makes the battle *feel* alive through code-driven animation and timing. Everything
from M0–M1 stays unless stated.

## Stack
- Unchanged. Python 3.11+, pygame, no new dependencies. No image/sound files.

## What's new
1. **Action animation.** When a combatant acts (Attack or Fire), it visibly **lunges**
   toward its target and returns to position (~0.3–0.4s round trip). Damage resolves
   at the contact point of the lunge.
2. **Hit reaction.** The target **flashes** (e.g. white) and **shakes** briefly when it
   takes damage.
3. **Floating damage numbers.** On a hit, the damage value appears over the target and
   **rises and fades out** over ~0.7s. (Fire's numbers may use a distinct color.)
4. **Smooth bars.** HP and ATB bars **interpolate** toward their target value instead of
   snapping.
5. **Idle motion.** Living combatants have a subtle **idle bob**.
6. **Death.** On reaching 0 HP, the combatant **fades out / sinks** rather than vanishing
   instantly, before the Win/Lose screen.
7. **Background.** Replace the blank fill with a simple drawn background (gradient and/or
   a floor band). Still no image assets.

## Timing rule (avoid race conditions)
While an action animation is playing, **pause all ATB filling**. Resolve the action,
play the hit reaction, then resume. One action animates at a time. Input is ignored
during an in-progress action.

## Refactor (sets up the future sprite milestone)
Route **all** per-combatant drawing through a single function/method, e.g.
`draw_combatant(surface, combatant, offset)`. Position offsets (lunge, shake), the
flash, and the death fade are applied here. The goal: a later milestone can swap the
shape for a sprite by changing this one function, leaving animation logic untouched.

## Done criteria
- [ ] Attacker lunges toward the target and returns, for both Attack and Fire.
- [ ] Target flashes and shakes when it takes damage.
- [ ] Damage numbers float up and fade over the target.
- [ ] HP and ATB bars animate smoothly rather than snapping.
- [ ] Living combatants idle-bob.
- [ ] A defeated combatant fades/sinks before the result screen.
- [ ] Non-blank drawn background.
- [ ] All combatant drawing goes through one swappable function.
- [ ] ATB pauses during an action; no input is accepted mid-action; no crashes.

## Explicitly DEFERRED — out of scope for M2
Real sprites / image assets · sound · particle systems · screen shake on the whole
view · camera · items · multiple spells · elemental weaknesses · party · multiple
enemies · status effects · levels/XP/equipment · overworld · tile maps · NPCs ·
dialogue · save/load.
