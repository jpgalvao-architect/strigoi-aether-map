# Pets

The **Pets** tab combines the catalogue, favorites, and your collection.
Version 0.10.0-beta.4 includes original portraits for 208 pets. The reference
catalogue does not guarantee availability in every region.

## Sync your collection

1. Open Azphelumbra. The counter also works if your character is already logged in.
2. In **Pets**, check your region and leave **Sync with game** enabled.
3. Favorite the pets to track. Received gains show **+N souls this capture**
   even before the collection total is known.
4. Open a pet's details in game. Two matching readings confirm **Pet Insight**,
   souls and the displayed target, without filling fields or importing files.
   `Lv. 2 (63/75)` means **Insight 2, 63/75 souls**, not the separate genus level.
5. After this reading, the counter tracks the total and subsequent gains.
   The screen total already includes earlier pickups; they are not added twice.

Connection reading uses Npcap, shared with Combat and Routine. Visual reading
reuses menu capture and only analyzes pet details when the Pets menu is recognized.
Images and screen text stay in memory.
Turning sync off does not
delete your collection. Manual records work without Npcap. Profiles are
separate by region, server, and character. Collection data stays on this PC.

If capture started after login and character identity has not arrived, gains
and screen readings stay in the current capture without modifying a saved
profile. Open the app before character login to save character-bound sync.
Reconnecting or switching characters resets capture gains. Received gains do
not establish a collection total without an initial reading; capture gaps can
make the gain counter partial.

**Pet Insight** differs from the genus level shown in the game. Unread
progress stays unknown instead of becoming zero. **Adjust manually** is a fallback:
manual values remain saved, but a confirmed screen reading displays the current
game value. The panel distinguishes manual and saved records from synced values.
Importing preserves a previous copy, and exporting creates a backup.

The initial snapshot matched the game in two SA logins. Kailin and Duduka
soul gains were received live in SA. Level-up events still need a live check.
After a data gap or an unresolved level-up, reopen this pet's details to sync
its total. User-provided SA screenshots were read as 62/75 and 63/75; the
screen-to-pickup sequence passed controlled tests. Live capture after installing
this correction still needs verification.

## Choose what to track

Search by pet or monster name and filter by family, map, progress, or
favorites. Choose an Insight goal and mark **Favorite**. Acquiring a pet
does not remove its favorite status.

Enable **Show pets panel**, or use **Pets panel** in the quick menu. The
compact view shows one favorite; the expanded view shows up to three with
scrolling for the rest. Drag the title, lock its position, and change opacity
in Pets. **Restore panel** brings it back on screen. Closing the panel keeps
sync running. Alt+Tab and recognized menus temporarily hide it.

## Find farming locations

Use **View locations in Atlas** in a pet's details. Pets can appear alongside
cubes and gatherables, using the same choices on the map overlays. **On maps**
can include all pets, favorites, or pending goals.

The 11,624 locations are documented monster spawn references for the complete
Altgard and Verteron maps, marked as possible sites. Current presence and
regional compatibility are unconfirmed. Pets without a mapped location
remain searchable without an invented marker.

This version tracks collection progress and reference sites. It does not yet
track moving NPCs or display live radar distance and direction. See
[sources](SOURCES.md) and `THIRD_PARTY.md` for provenance and rights.
