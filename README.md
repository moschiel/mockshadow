# mockshadow

**Motivation**: I wanted to run and debug an embedded firmware as a regular process on my PC, mocking every hardware dependency and without needing the real board. I wasn't interested in unit testing — I actually wanted to simulate the full firmware execution. So I created **mockshadow** to help me mock hardware dependencies more easily.

**mockshadow** is a command‑line tool that creates a _shadow tree_ of your C project, where any **function, variable, macro, typedef, enum, struct or union** can be replaced by a user‑written mock implementation — all without touching your original source files.

Instead of manual patches inside the production sources, the developer creates parallel files (prefixed with **__**__mock__**__**) containing textual instructions that specify _what_ to replace and _with what_. 
When you run `mockshadow mock`, the tool locates the symbol in the original code and generates a modified copy in an output folder.

mockshadow **does not compile** anything: it only performs textual substitution and produces a copy of the sources already modified. It's up to the user to write Makefiles, CMakeLists, or any other build system needed to compile and run the mocked code on their PC.

In short: the real code stays clean and version‑controlled; the shadow can undergo any mutation needed for testing.



**To install all dependencies**:

On Ubuntu or WSL:Run `python3 setup.py`

On Windows: In development





