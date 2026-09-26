# Recipe reference

Files retain the original extension. Sources/recipes use Latin-1. Markers are C
comments. First-line `//__MOCK_COPY_FILE_CONTENT__` enables transformations;
otherwise the whole recipe replaces the source. Original-content insertion in
discard mode is a legacy TODO, not a supported feature.

Phases run in this order, not arbitrary interleaving in the recipe:

1. `__MOCK_REPLACE_TEXT_LINE: literal` plus exactly one replacement line, or
   `__MOCK_REPLACE_TEXT_START: literal` through `__MOCK_REPLACE_TEXT_END`.
2. `__MOCK_REMOVE: type name [flags]`.
3. `__MOCK_REPLACE_CODE_LINE: type name [flags]` plus one replacement line, or
   `__MOCK_REPLACE_CODE_START: type name [flags]` through `__MOCK_REPLACE_CODE_END`.
4. `__MOCK_TOP_START` / `__MOCK_TOP_END` and BOTTOM blocks as encountered.
5. `__MOCK_ADD_BEFORE_LINE: type name [flags]` / `__MOCK_ADD_AFTER_LINE` plus
   one line; or `__MOCK_ADD_BEFORE_START: type name [flags]` through
   `__MOCK_ADD_BEFORE_END` (likewise AFTER_START / AFTER_END).

Types: function, prototype, macro, global, typedef, struct, union, enum,
extern-variable, extern-function. Directive flags join `extractorCFlags`. Legacy
flag splitting does not preserve quoted whitespace; avoid spaces in include paths
passed through extra flags. Source paths themselves may contain spaces.

```c
//__MOCK_COPY_FILE_CONTENT__
//__MOCK_TOP_START
#include "__additional__battery.h"
//__MOCK_TOP_END
//__MOCK_REPLACE_CODE_START: function ReadBattery -DENABLE_ADC
int ReadBattery(void) { return SIM_BATTERY_MV; }
//__MOCK_REPLACE_CODE_END
```

Top blocks in headers go inside detected header guards. Text replacement is
literal and may replace multiple occurrences. Prefer symbols for whole functions.
Bottom blocks in C sources append after the final line (outside the last
function), including when EOF lacks a newline. In headers they precede the final
detected `#endif`, or append at EOF when no `#endif` exists. The historical
off-by-one insertion was corrected; rebuild generated trees after updating.
LINE inserts only the following line; use START/END for multiline replacements.
Later lookups see earlier edits. Missing symbols/text are errors. First-match
extraction and tolerated Clang diagnostics mean audit is not semantic validation;
inspect generated code and compile to detect signature/definition conflicts.
