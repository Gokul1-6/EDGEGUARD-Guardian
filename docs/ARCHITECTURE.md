# Architecture
Windows background agent -> local collectors -> event normalizer -> policy engine -> SQLite -> local Flask dashboard.

Collectors:
- Process/activity observation
- Local browser history observation
- Battery state
- Future documented Windows microphone/camera telemetry adapter

AI layer:
- AI service classification
- Optional local event-risk model
- Optional local language model for summaries

The architecture deliberately separates always-on lightweight monitoring from heavier AI inference.
