# Migrating to Mockshadow 2

This is a breaking format and CLI change. No runtime compatibility loader exists.

1. Capture a generated-tree baseline using the previous tool and the same source.
2. Set formatVersion to 2 and mocksDirectory to a dedicated input folder.
3. Move each recipe to a descriptive C/C++ filename anywhere under that folder.
   Declare __MOCK_TARGET using the old original-relative destination and explicitly
   declare __MOCK_MODE: patch (old copy marker) or replace (old discard/default).
   Remove old COPY/DISCARD markers. Keep directive bodies and Latin-1 bytes.
4. Move additional sources outside the recipe folder. Map each source/destination
   in additionalFiles. Existing __additional__ names are ordinary names now;
   retaining output names avoids unnecessary include/build changes.
5. Update tests, build scripts, ignored generated inputs, manifests and editor tasks.
   Use mock --force instead of remock, --details instead of positional details,
   and --version instead of version. Remove clone-tree/unmock calls.
6. Regenerate and compare output hashes (excluding manifests), audit, compile and
   test each consumer. Original inputs must remain unchanged. Generated output is
   always shadow_output, with staging, rollback, content cache and project lock.

Missing/excluded targets, duplicate targets, unsafe paths, ambiguous destinations
and malformed headers are errors. No recipes or model sources are deleted by CLI.
The original firmware remains separate. Physical IO guards must remain enabled.
