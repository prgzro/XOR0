# Setup lifecycle edge cases

Type: grilling
Status: wontfix
Blocked by: 03, 07

## Question

Pin down the state machine's edge cases. What happens when: price closes beyond 0° (through the Origin)? Price reaches 360° with no 45° pullback? The pullback closes below 45° but above 0°? The Origin changes mid-setup under the confirmed-Origin policy? Two setups (bullish and bearish) are live on one symbol? A new candidate appears while a trade is open on that symbol? Also, which states can repeat for the same Origin? Output: the full transition table with invalidation reasons.

Carried in from the repaint research (resolved): decide (a) whether a 0° breach means a candle **close** beyond 0° or any **wick**, and (b) whether to skip or stop setups whose frozen Origin is about to drop out of the 270-bar window. See `docs/research/v2-repaint.md`.
