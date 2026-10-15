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

2026-10-14 roster recovery: optional CP/stat-tail failures no longer discard
validated name/server/class fields. Next-slot recovery scans at most128bytes
with name, server, class and level checks, independently of the optional CP
offset. Vacant or unreadable earlier slots no longer hide valid later members;
unreadable mandatory fields still mark the roster incomplete.

2026-10-14 pets: add bounded readers for collection 0090, soul gain 0D90,
and insight-level 1490, based on the separately attributed GPLv3 layouts in
PET-PROTOCOL-NOTICE.md. Reject complete snapshots on duplicate IDs,
truncation, oversized lists, or out-of-range fields; count rejected pet
records separately from damage. The bridge forwards only typed pet fields
and counters. No packet recording, injection, or network transmission is added.
