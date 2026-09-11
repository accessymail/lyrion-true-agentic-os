# Voice-First Architecture

Voice-first conversational architecture for Lyri.

## 1. Architecture

Microphone
      ↓
Voice / Audio Perception
      ↓
VAD
      ↓
Turn Detection
      ↓
Streaming ASR / Realtime Audio Model
      ↓
Intent + Context
      ↓
PIAE
      ↓
Cognitive Runtime
      ↓
Decision / Action
      ↓
Streaming TTS / Realtime Audio
      ↓
Speaker

## 2. Voice Identity and Cloning

Voice Identity is a first-class component of Lyri's Voice Runtime.

Voice Identity includes:

- stable Lyri voice identity
- voice profile
- provider/model binding
- supported vocal characteristics
- speaking-style configuration
- voice versioning
- voice evaluation state

Voice Cloning is a controlled voice-generation capability used to
produce speech consistent with the configured Lyri voice identity.

The architecture must support:

Voice Identity
      ↓
Voice Profile
      ↓
Voice Provider / Model
      ↓
Voice Cloning / Synthesis
      ↓
Streaming TTS / Realtime Audio
      ↓
Speaker

Voice Identity must remain separate from:

- human identity authentication
- speaker identification
- authorization
- capability permissions
- execution authority
- security policy

A cloned voice is an expression mechanism, not an authentication
credential and not an authorization mechanism.

Reference voice data, cloned voice configuration and related metadata
must remain subject to privacy, access-control, provenance, retention
and deletion policies.

Provider-specific voice-cloning implementations must remain behind
the provider-neutral Voice Runtime interface.

## 3. Required Voice Properties

The Voice Runtime must support:

- low latency
- streaming
- barge-in
- interruption handling
- session continuity
- voice-state management
- voice evaluation

## 4. Provider Architecture

Voice providers must remain replaceable implementation components.

Lyri
  ↓
Voice Runtime
  ↓
Voice Provider Interface
  ├── Provider A
  ├── Provider B
  ├── Provider C
  └── Local / Self-hosted Model

No individual voice provider is an architectural dependency.

## 5. Voice Authentication Boundary

Voice authentication and speaker identification are security
capabilities separate from Voice Identity and Voice Cloning.

Voice Identity
    ≠
Speaker Identity
    ≠
Voice Authentication
    ≠
Authorization
    ≠
Execution Authority

Voice output must never grant or imply execution authority.

## 6. Privacy and Governance

Voice reference data, voice profiles, generated voice artifacts and
voice-related metadata must follow Lyrion data-governance controls,
including:

- minimization
- purpose limitation
- access control
- provenance
- retention
- deletion
- auditability

Voice cloning must operate within the same security and governance
boundaries as other model and execution capabilities.
