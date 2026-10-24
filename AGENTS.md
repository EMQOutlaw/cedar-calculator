# Development policy

- Work only in this standalone repository. Never patch the CEDAR Shell checkout.
- All future updates target `dev`. Never commit directly to `main`; main is a
  controlled baseline. Coordinator owns branch creation, integration and promotion.
- No commit, push, remote creation, installation, activation or publishing without
  the appropriate explicit authorization. Passing tests is not release approval.
- Keep the app self-contained: no Config, ShellState, shell services or Omarchy.
- Preserve compact 360x560 behavior, keyboard focus, error recovery and memory-only
  bounded history. Use Theme tokens and the existing component vocabulary.
- Write a failing regression before behavior changes. Run engine, Python installer
  tests, real offscreen QML and QML lint. Separate offscreen from native evidence.
- Do not alter CalculatorEngine.js merely to accommodate UI or test expectations.
- Never introduce eval, shell arithmetic, secrets, network or silent persistence.
- Preserve GPL-3.0-only licensing and provenance; license changes require owner approval.
