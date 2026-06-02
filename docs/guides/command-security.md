# Signed MQTT Commands

Edge agents accept control commands only as **versioned, signed JSON envelopes** on the
`edge/commands` topic when `security` is configured.

## Envelope format

Required fields (unknown fields are rejected):

- `version` (must be `"1"`)
- `command_id` (UUID)
- `timestamp` (unix epoch seconds)
- `nonce` (unique per issuer)
- `issuer` (trusted signer id)
- `device_id` (target edge agent id)
- `action` (currently `deploy`)
- `params` (action-specific object)
- `signature` (base64 Ed25519 signature)

## Signing

Canonical signing input is JSON with sorted keys and no `signature` field.

Configure trusted signers under `security.trusted_signers` using Ed25519 public keys
(`public_key_hex`).

## Agent policy

`security.policy` controls authorization after signature verification:

- `allowed_actions`
- `allowed_deployment_types`
- `allowed_images` (fnmatch patterns, docker)
- `allowed_yaml_roots` (kubernetes manifest paths)

## Replay protection

The agent stores `(issuer, nonce)` pairs for `security.nonce_ttl_seconds` and rejects
duplicates. Timestamps must be within `security.max_clock_skew_seconds`.

Default store is SQLite (`security.replay_store.type: sqlite`). For multiple agent
replicas sharing nonce state, use Redis (`type: redis`) — see [security-operations.md](security-operations.md).
