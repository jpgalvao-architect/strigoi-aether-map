# Azphelumbra

**AION 2 Companion App · 0.10.0-beta.7 · Windows x64**

Beta 7 automatically tracks the fixed minimap center and removes manual arrow
setup. Stop numbers and other icons no longer interrupt positioning; advancing
uses a brief confirmation near a stop. Alt+Tab, menus, and the full map continue
to suspend tracking.

Beta 6 adds **Routes**: choose Atlas targets, organize stops, edit passages,
and follow the path on the minimap and full map. The guide switches between
Strip and Guide through its menu. Automatic progression still needs live movement validation on SA. Visits
do not confirm collection; suggested lines do not guarantee walkable passages.
See [Farming routes](docs/ROUTES.en-US.md).

Beta 5 adds daily Battlefield windows and counts down to matchmaking closing. Immortal Gartua gets a one-time prediction read from the in-game countdown, without assuming daily spawns. Abyss bosses use a labeled Global reference, not individually confirmed on SA. See [Events and timers](docs/EVENTS.en-US.md).

Beta 4 tracks soul gains even when the app starts with the character already logged in. Without an initial total, it shows capture gains; opening pet details confirms the total without double-counting earlier pickups. Unidentified readings stay in memory without modifying saved profiles. Menus such as Enhancement require title, tabs, separator and close-button evidence to hide overlays. See [Pets](docs/PETS.en-US.md).

Routine adds a character Overview and passively reads basic and charged
Odyle Energy. Its overlay switches between Compact Pulse and Strip, saving
style, position, and tracked resources. The initial reading matched an SA
login; caps and recharge rules are not assumed. See [Routine](docs/ROUTINE.en-US.md).

The Vigília interface keeps module controls beside your session. The Impacto combat overlay shows DPS bars with class icons and colors. The compact Fita event strip expands to show the day’s schedule. Use the floating emblem to open quick controls. Existing preferences, visits and collections are preserved.

Beta 12 puts frequency controls in **Overlay → Overlay performance**. Choose 15–360 Hz for drawing and 10–60 fps for minimap capture (up to 30 fps on the full map), with immediate changes and saved preferences. New installations start at 60 Hz/30 fps; existing choices are preserved. Stationary markers no longer redraw continuously, and visual processing uses fewer threads. In-game FPS improvement still needs checking after updating.

Beta 11 adds Pets with 208 original portraits, favorites, Insight goals, a map filter, and a compact quick-menu panel. The initial collection matched two SA logins. Farming sites are client references without guaranteed current presence; live radar distance and direction are not available yet. See [Pets](docs/PETS.en-US.md).

Beta 10 makes party decoding more resilient: optional combat-power metadata
cannot discard valid identities, and later members can be recovered after
vacant or unreadable records. Recovering three rows into a five-player
ranking passed controlled tests; confirmation in a new SA instance is pending.

Beta 9 improves Spiritmaster summon attribution: announced owners take
priority, incomplete updates preserve links, and cast signals plus a
conservative PvE combat inference can reconcile ownerless spirits. Ambiguous
cases stay unattributed. The eight Global classes now use original official
PNG icons and colors. Attribution passed controlled tests; live SA
confirmation is still pending.

Beta 8 fixes overlays disappearing during gameplay: an X-shaped screen detail alone cannot identify a menu. Alt+Tab hiding still works. Menus require local recognition of known titles; coverage is not universal. The full map keeps its markers, capture continues, and old Sonar alerts are not replayed.

The app doubles minimap symbols, adds arrows to cube sites with supplied height flags, and adds an intensity bar and recent history to Sonar. Arrows follow the source group's relative height; the bar estimates the recognized sound and is affected by game volume. Its relationship with in-game proximity still needs validation.

The app shows the combat panel in recognized dungeons and 1v1/5v5 arenas and hides it on exit. Entry and exit signals were observed for one map per arena mode in SA; other rotating maps still need identification. PvP totals include outgoing attacks by confirmed participants and exclude received damage. Calculation remains experimental without live accuracy validation; the complete 5v5 team roster is not confirmed yet. Quick controls can hide the panel without stopping capture.

[App website](https://jpgalvao-architect.github.io/strigoi-aether-map/) ·
[Installer and downloads](https://github.com/jpgalvao-architect/strigoi-aether-map/releases/tag/v0.10.0-beta.1) ·
[Português](README.md)

Your exploration journal: maps, gatherables, possible cube locations and
events. Aether, the Asmodian-inspired vampire, joins your journey.

The 0.9 beta adds experimental instance damage tracking, a compact overlay,
observed DPS/share, explicit summon ownership, target filtering and local
history. SA capture still needs validation; results are marked partial.
See [Combat](docs/COMBAT.md) for current scope and limitations.

Run `StrigoiAetherMap-Setup-0.10.0-beta.1.exe`, choose English and review the terms
before accepting. Setup installs for the current user and includes an
uninstaller and corresponding source code. Existing preferences and visits
are preserved. English is the default for a fresh installation; an explicit
language preference from an earlier installation remains yours.

If Npcap is missing, Setup downloads the verified official installer and
opens the publisher's wizard in the same flow. Complete that wizard and its
Windows permission prompt. No Npcap copy is embedded in our download.

For the portable edition, extract the entire ZIP and open
`StrigoiAetherMap.exe`. Keep `_internal` beside the executable. Python does
not need to be installed. Open **Settings → App language** to switch
between English (United States) and Portuguese (Brazil) immediately.
This changes the interface, not your region or event time zone.

Choose layers in the atlas or Overlay; the same selection applies to the
atlas, minimap and full map. Select only the minimap terrain once.
Opening the full map with M switches the overlay automatically; closing
it returns to the minimap. Set drawing and reading rates in **Overlay performance**, starting at 60 Hz/30 fps. Rates are limits, not performance guarantees.

In Events, enable the floating panel and select an event to track.
Expand it to view that event's times today; Automatic follows the next event.
Drag the header to move it.

For Sonar, open the game, refresh applications, select AION 2 and enable
Sonar. Audio is analyzed locally, without microphone access or recording.
It starts off each session. A possible-cube alert is a sound cue, not proof
of a cube or its exact location. Test visual alert is labeled as a test.

Click the floating mascot to expand quick controls for Sonar, maps, combat
and events. Drag it to move it. Hiding the combat panel keeps capture running.
Combat starts automatically when Strigoi opens and Npcap is available; turn
it off in Settings at any time.

Strigoi uses external overlays, screen-image recognition and Windows
application audio. It does not inject DLLs, modify game files, read game
memory or perform game actions. About explains hearing accessibility and
offers the complete [terms of use](docs/TERMS.en-US.txt).

The maps are real map images. Locations and schedules come from documented
community sources; none are invented runtime demonstration data.
Possible locations do not imply simultaneous spawns or individual SA
verification. Source notes, institution names and user notes may retain
their original language. English display names do not change source IDs,
coordinates, region or time zone.

Original code: GNU GPL version 3 only. See `LICENSE` and `LICENSE-NOTICE.md`.
Community maps/data: CC BY-NC 4.0, noncommercial use. Other assets and
dependencies retain their respective rights and notices in `THIRD_PARTY.md`.
Corresponding source and build scripts: `source/strigoi-aether-map-source.zip`.
Developer build instructions are in `README.md`; installer instructions are
in `docs/INSTALLER.md`.
