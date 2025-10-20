# mockshadow

## Motivation
I wanted to **run and debug embedded firmware for microcontrollers on my PC** while the real hardware is either unavailable or inconvenient.  Unit testing alone doesn’t cut it—I want to execute the *entire* firmware, see it interact, crash, leak, and behave similarly as it would on a microcontroller.

The problem: some legacy projects I have to debug are tightly coupled to HALs, registers, and inline assembly. Sprinkling preprocessor directivies like `#ifdef SIMULATION` everywhere quickly becomes un‑maintainable.  I needed a cleaner way.

**mockshadow** is the tool I wrote to make that possible.

---

## What mockshadow *is*
A CLI that builds a *shadow copy* of your C project where any function, variable, macro, typedef, enum, struct, or union can be swapped for a user‑written mock **without modifying the original source tree**.

---

## What mockshadow *does not* do
* ❌ *Generate* mocks for you – you still write the replacement code.
* ❌ Fix compilation errors automatically – you decide what must be mocked or stubbed.
* ❌ Compile or link – it only rewrites text.

---

## What mockshadow *does* very well
* ✅ Uses Clang to pinpoint symbols accurately (no brittle regex).
* ✅ Applies all substitutions in one shot, producing a clean *shadow tree*.
* ✅ Leaves the pristine firmware untouched and under version control.
* ✅ Eliminates the flood of pre‑processor directives usually required for simulation builds.

---

## Practical workflow
1. **Attempt to compile** the firmware natively – watch it fail on register access, inline ASM, HAL calls…
2. **Create a mock file** under `MOCK_TREE/…/__mock__*.c` or `.h`, containing directives that say *what* to replace and *with what*.
3. Run `mockshadow mock` – the tool clones the project, applies your mocks and writes the result to `SHADOW_OUT/…`.
4. **Build the shadow tree** with your favourite system (Make, CMake, VSCode tasks…).
5. Execute the firmware as a normal PC process, run sanitizers, fuzzers, debuggers—you name it.

---

## Installation
1. **Install clang-code-extractor submodule**
    Follow submodule installation instructions at path `clang-code-extractor/README.md`

2. **Execute Mockshadow Setup Script**
```bash
# Ubuntu / WSL
python3 setup.py

# Windows
python setup.py
```

3. **Add to Path (Windows only)**  
    On Windows, you must add mockshadow directory to PATH variable.

4. **Test installation**
```bash
mockshadow version
``` 

---

## Current status
The project is **experimental but functional**.  A hands‑on example that mocks a simple STM32 HAL project is on the way.

PRs, issues and feedback are welcome!
