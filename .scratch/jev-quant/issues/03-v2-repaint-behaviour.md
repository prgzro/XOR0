# Does V2 repaint its Origin?

Type: research
Status: resolved
Blocked by: 01

## Question

Given the auto-detect rule from ticket 01, when does V2 move its Origin as new bars arrive (including on the still-open bar), and what would a non-repainting, closed-bars-only version of the rule be? Replay history bar by bar with the inferred rule and measure how often and how far the Origin moves. Output: a confirmed-Origin policy candidate and how much it differs from what V2 shows live.

## Answer

If V2 re-applies the ticket-01 rule bar by bar, its Origin moves often: about 70 changes per 1000 bars on H1 and H4. 97–98 % are drop-outs. The Origin is the older extreme (median age about 232 bars), so it "crawls" along the left edge of the 270-bar window, moving the 90° level by a median 0.4 steps of 45° each time. The other 2–3 % are wick breaches beyond 0°, and every one flips direction: the older opposite extreme becomes the Origin and the levels jump about 8 steps.

On the forming bar, the Origin changes only through a breach, and such a change never reverts. Even so, V2's Origin survives only 62 % of 20-bar spans and 38 % of 50-bar spans. A setup will therefore look different in hindsight.

Proposed policy:
- Evaluate the rule at each new bar on the 269 closed bars (shifts 1..269), with direction from `Close[1]`. This matches V2 live on 99.9 % of ticks, with at most a one-bar lag.
- Give each Origin an identity `(sym, tf, barTime, price, H/L, N)`.
- Freeze the Origin and Space per setup, and invalidate only on a breach of 0°, never on a drop-out.

Still open: whether V2 really recomputes live or only on reload (HITL). [write-up](../../../docs/research/v2-repaint.md)


**Update (ticket 13):** V2 does not recompute live; its Origin is fixed from attach or the last Reset (864 H1 bars unchanged in the Tester). The figures above describe a rolling rule, which is what our EA must use across many symbols; the policy stands as our own design, with window 270.
