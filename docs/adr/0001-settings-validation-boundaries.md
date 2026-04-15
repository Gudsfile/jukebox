# ADR 0001: Settings Validation Boundaries

## Status

Deprecated

Reason: `discstore` has been replaced by `jukebox-admin`, which is located in the `jukebox` module.

## Context

Jukebox now resolves settings in multiple stages:

- persisted settings loaded from `settings.json`
- effective settings produced by merging defaults, file values, environment overrides, and CLI overrides
- runtime configs produced for specific entrypoints such as `jukebox` and `discstore`

Both `jukebox` and `discstore` read from the same merged settings tree, but they do not require the same invariants to operate. A recent regression showed the risk of enforcing runtime-specific rules too early: validating the effective settings tree for an active Sonos target caused `discstore` admin flows and effective settings inspection to fail even though they do not need a runnable jukebox player.

## Decision

Validation must live at the narrowest layer that actually needs the invariant.

The project uses three validation layers:

1. Persisted settings validation

- Enforces JSON shape, allowed keys, migrations, and scalar constraints that are safe to require for any consumer.
- Lives in the settings repository and shared settings models.

2. Effective settings validation

- Enforces that the merged settings tree is a valid shared `AppSettings` object after defaults, file values, environment overrides, and CLI overrides are combined.
- Must not enforce invariants that are only required by one runtime.

3. Runtime config validation

- Enforces operational requirements for one specific app or subsystem.
- Lives on resolved runtime models such as `ResolvedJukeboxRuntimeConfig` and `ResolvedAdminRuntimeConfig`.
- Examples:
  - `jukebox` may require an active Sonos host when `player_type == "sonos"`.
  - `discstore` should only require admin- and library-related settings.

## Consequences

- `discstore` can inspect and use shared settings even when the jukebox runtime configuration is incomplete.
- `jukebox` still fails fast when its resolved runtime config is not runnable.
- New validation rules must be placed intentionally:
  - if a rule applies to any stored or merged settings, it belongs in the shared models or repository layer
  - if a rule only affects one runtime, it belongs in that runtime's resolved config

## Review Checklist

When adding validation, ask:

1. Which caller is harmed if this invariant is false?
2. Do all callers of this layer require the invariant, or only one runtime?
3. Can the rule move onto a resolved runtime model instead of the shared effective settings layer?

If the answer is "only one runtime", the validation should not live in shared settings resolution.

## Testing Guidance

Boundary tests should exist for runtime-specific invariants:

- incomplete runtime-specific settings should still be inspectable via persisted/effective settings APIs
- the same incomplete settings should fail when resolving the affected runtime config

This protects shared settings consumers from accidentally inheriting unrelated operational requirements.
