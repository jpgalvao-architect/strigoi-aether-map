# Pet record layouts

The pet collection, soul pickup and insight-level record layouts were checked
against the public GPL-3.0-only source of Wany917/aether-meter:

- Commit: `516d9c4e2bc76b4892fe645c19475ef86ae7ad99`.
- File: `crates/engine/src/pets.rs`.
- Source: https://github.com/Wany917/aether-meter/blob/516d9c4e2bc76b4892fe645c19475ef86ae7ad99/crates/engine/src/pets.rs

That source attributes these layouts to taengu/A2Tools-DPS-Meter's GPL-3.0
`src-tauri/src/plugins/decoder.rs` tests. The complete GPLv3 text is present
in this vendor directory's LICENSE and in the project root.

Strigoi implements bounded C# readers for these layouts and its own collection
store and UI. It rejects truncated, duplicated and out-of-range collection
records before emitting a snapshot. Regional validation is tracked separately;
the availability of a public layout is not proof of South America compatibility.
