# Voice Provider Abstraction — 19.4.4

**Status:** Implemented — Validated
**Track:** Voice-First
**Architecture:** Provider-neutral

## Objective

Establish a provider-neutral Voice Provider control-plane and execution
abstraction so Lyri's Voice Runtime can use replaceable voice providers
without coupling core runtime logic to a vendor SDK or transport.

## Architectural Boundary

```text
Lyri Voice Runtime
        |
        v
Routing Policy
        |
        v
Voice Provider Registry / Routing View
        |
        v
Voice Provider Gateway
        |
        v
Voice Provider Interface
        |
        +---- Provider Adapter A
        +---- Provider Adapter B
        +---- Provider Adapter C
        +---- Local / Self-hosted Provider
