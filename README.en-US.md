# Strigoi Aether Map

**AION 2 Companion App · 0.9.0-beta.4 · Windows x64**

Beta 0.9.0-beta.4 automatically shows the combat panel in recognized instances and hides it on exit. Quick controls can disable panel display without stopping measurement. Arena 1v1/5v5 identification and measurement still await live validation and are not advertised as confirmed.

[App website](https://jpgalvao-architect.github.io/strigoi-aether-map/) ·
[Installer and downloads](https://github.com/jpgalvao-architect/strigoi-aether-map/releases/tag/v0.9.0-beta.4) ·
[Português](README.md)

Your exploration journal: maps, gatherables, possible cube locations and
events. Aether, the Asmodian-inspired vampire, joins your journey.

The 0.9 beta adds experimental instance damage tracking, a compact overlay,
observed DPS/share, explicit summon ownership, target filtering and local
history. SA capture still needs validation; results are marked partial.
See [Combat](docs/COMBAT.md) for current scope and limitations.

Run `StrigoiAetherMap-Setup-0.9.0-beta.4.exe`, choose English and review the terms
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
it returns to the minimap. The draw rate is a target, not a guarantee.

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
