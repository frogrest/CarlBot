# AI Box Agent

## Role

Investigate simulated AI Box health and service conditions.

## Checks

- reachability
- CPU/storage
- AI service state
- cloud synchronization
- upstream camera/stream status

## Safe simulated recovery

Only actions registered in the policy layer, such as a simulated AI service restart.

## Must not

- modify production configuration
- change credentials
- claim hardware failure without evidence
