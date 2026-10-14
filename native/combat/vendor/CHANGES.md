# Local changes

Initial import: 2026-10-12, pinned commit in NOTICE.md.
The Strigoi bridge uses only passive live capture, without recording.
LiveCapture filters incoming exact game-owned connection tuples in BPF and
again before decoding, rejects unfiltered adapter overrides, removes raw
recording and closes the device when game connections disappear. Dropped
packet counts survive adapter reopen. PacketPipeline resets sequence state
on SYN and removes finished flows, avoiding connection-tuple reuse.
Flow enumeration and TCP delivery are synchronized. Multiple simultaneous
connected clients are refused rather than merged into an invalid ranking;
same-name launcher/guard processes without eligible connections are ignored.
Connection ownership is retained from the TCP table for this distinction.
Party rosters report completeness so a partial decode cannot silently classify
unread teammates as outsiders. Empty trailing slots are distinguished from a
failed member decode. The parser's original wire validation remains in place.

2026-10-14: spirit-anchor owner ids take precedence over inline owner names;
ownerless kind 0x1C now emits SummonSeenEvent like the other summon kinds.
The bridge forwards already-decoded raw CastEvent variants. Normalized damage
PowerScalar is preserved for bounded, ambiguity-rejecting reconciliation.
No packet recording or additional network access is introduced.
