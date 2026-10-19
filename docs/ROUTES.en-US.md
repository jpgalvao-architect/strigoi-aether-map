# Farming routes

Open **Routes** in the sidebar, or use **Create route** in the Atlas,
Gatherables, or pet details. Routes use locations recorded in the Atlas.

## Create a route

1. Choose a map and one or more targets, such as Azpha, cubes, or pet souls.
2. Choose **Loop** to return to the start, or **One way**.
3. Adjust the number of stops. The planner groups nearby locations and
   suggests a visit order. Use **Choose starting stop** to pick your entry.
4. Check the preview. **Edit passages** adds vertices between stops;
   **Undo edit** restores the previous edit.
5. **Save** the route locally, or select **Start on minimap**.

If your target has no recorded locations, use **Add my locations**. This starts
a new route using locations you mark on the map. At least two are required.
**My routes** lets you load, delete, import, and export JSON routes. Imported
files can be up to 16 MB.

## Follow the route in game

The path appears on the minimap and full map using the existing overlay
recognition. The highlighted number marks the next stop. If no minimap area
is configured, starting a route opens area selection.

Your character stays at the center of the minimap terrain; only the compass
rotates. With the game in the foreground and the terrain recognized, the app
projects that center into the Atlas and tracks stops automatically. You do not
need to identify or calibrate the arrow. Icons and stop numbers can cover it
without interrupting positioning. Tracking is suspended on the full map:
its center can be panned and does not represent your character.

Select only the minimap terrain, excluding the title and controls below it.
Select the area again after changing resolution, scaling, or monitor.

The **Strip** guide shows the target and stop in 303 × 38 pixels. Use **···**
to switch to **Guide**, which adds a second status line. You can pause,
resume, skip a stop, repeat, or end the route. Drag to reposition it. The quick
menu can hide the guide without ending the journey.

Advancing requires fresh readings and about 0.35 seconds near the stop. Menus,
Alt+Tab, or lost recognition suspend tracking while preserving progress.
Changing area or character pauses the route until you resume it.
Without a reliable reading, use **Skip stop** to advance manually.

## Review passages

Dashed lines are suggested geometric links. The app has no walkable road
network and does not know every wall, cliff, or elevation change. A line
does not guarantee a walkable passage.

After editing or recording a section, check it in game and select **I reviewed
the edited passages**. Only these sections become solid and can be reused
in the same direction between the same locations. Imported routes require
a new review.

**Record my journey** stores recognized coordinates only. Start recording
before visiting the first stop. A section interrupted by lost recognition
is never connected to the next one. **Review recorded journey** shows complete
sections so you can check and save a new route.

## Understand the indicators

- Visiting stops does not confirm collection or increase item counters.
- Atlas locations are references; current availability depends on the game.
- Altgard's 150 Azpha locations come from community data and are not
  individually confirmed on SA.
- There are no estimates for meters, yield, respawn, or arrival time.
  The module does not move your character or send commands to the game.
- Projection, recording, and progression passed controlled tests. Automatic
  progression still needs validation during a real SA session.

Saved routes live in `routes.json` in the app's data folder. Active journeys
do not resume automatically after restarting the app. Your frequency setting
in **Overlay → Overlay smoothness** continues to apply.
