# Odyle energy record layout

The bounded C# reader follows the documented entry-counter layouts in
taengu/A2Tools-DPS-Meter, GPLv3:

- Commit: `db1cea2d7ec75dbc78c2f31171115cbb733a3886`.
- Source: https://github.com/taengu/A2Tools-DPS-Meter/blob/db1cea2d7ec75dbc78c2f31171115cbb733a3886/src-tauri/src/capture/stream_processor.rs
- Functions: `entry_count_at`, `odyle_energy_of`, `odyle_energy_in_list`,
  `odyle_energy_in_update`; related Odyle fixtures.

Our implementation rejects ambiguous list matches and malformed/overflowing
varints. Updates require the key established by an absolute list. Missing basic
or charged components in a recognized masked entry are zero by the format;
absence of an energy entry is not zero. Cap, refill rules and reset times are
not inferred from this record. Character binding is handled separately and
does not reuse a previous character when a login list precedes identification.

The complete GPLv3 license is included in this directory and the project root.
Availability of this layout alone does not establish regional validation.
