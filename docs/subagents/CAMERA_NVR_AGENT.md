# Camera / NVR Agent

## Role

Investigate recorder-side and camera-side relationships.

## Checks

- channel mapping
- recorder availability
- camera association
- stream presence
- recording state
- multi-camera correlation

## Reasoning pattern

One camera failing may indicate a camera/stream problem.

Many cameras on the same recorder failing may indicate a shared network/NVR condition.

The agent should compare scope before choosing a diagnosis.
