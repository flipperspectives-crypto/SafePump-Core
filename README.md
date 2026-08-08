[![Sponsor](https://img.shields.io/badge/Sponsor-❤%20flipperspectives-2ecc71)](https://github.com/sponsors/flipperspectives-crypto)

# SafePump-Core

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![good first issues](https://img.shields.io/github/issues/Nosferatus1988/SafePump-Core/good-first-issue?label=good%20first%20issues)](https://github.com/Nosferatus1988/SafePump-Core/issues?q=is%3Aissue+is%3Aopen+label%3A%22good-first-issue%22)
[![Solana](https://img.shields.io/badge/Solana-Anchor%201.0-9945FF)](https://www.anchor-lang.com/)

Anti-MEV bonding-curve launchpad on Solana, written in Anchor/Rust.

This repository is a devnet MVP. It can initialize a launch, route first-slot
snipes into a vesting vault, let normal buyers buy and sell on the bonding
curve, and mark a curve complete when an optional graduation target is reached.

🌐 Live site: [safepump-core.com](https://www.safepump-core.com)

## 🛠️ Looking for contributors

SafePump-Core is open source and actively looking for collaborators. If you know **Rust + Anchor**, **TypeScript + Solana web3.js**, **Next.js + wallet-adapter**, or just want to write docs and tests — there's a place for you.

- 🎯 [Open good-first-issues](https://github.com/Nosferatus1988/SafePump-Core/issues?q=is%3Aissue+is%3Aopen+label%3A%22good-first-issue%22) — scoped, beginner-friendly tasks
- 📖 [CONTRIBUTING.md](CONTRIBUTING.md) — workflow, conventions, quick start
- 🔒 [SECURITY.md](SECURITY.md) — responsible disclosure
- 💬 [Discussions](https://github.com/Nosferatus1988/SafePump-Core/discussions) — design questions, RFCs

Currently a solo project; aiming for 3-5 active contributors before mainnet. Contributors will be credited and may be eligible for token allocation if a mainnet launch happens (see [CONTRIBUTING.md](CONTRIBUTING.md#recognition)).

## Program ID

`FMAhGG8ETyqnd4zan4HBdLRPEQvk7Cvc6kzWbsvnXj5q`

Deployed on devnet with upgrade authority
`9WPztx4YNSrLr1ZD61kKziwqryQhrrTPomx6HodyJCS9`.

The matching local keypair is generated under `target/deploy/` and is ignored by
git. Do not commit deploy keypairs.

## SolPump Mainnet Prep

The public token name is staged as `SolPump` with draft symbol `SOLPUMP`.
Mainnet token creation is prepared under [mainnet-launch](mainnet-launch/), but
no mainnet transaction is automated or executed by the repository scripts.

Generate the mainnet token plan:

```bash
npm run token:plan
```

The investor-facing static site is under [site](site/). Open
[site/index.html](site/index.html) directly in a browser, or publish it with the
example GitHub Pages workflow in [docs](docs/) after Pages is configured for
GitHub Actions.

## Anti-MEV model

Token launches on Solana get sniped in the first slots by bots that buy a large
piece of supply, wait for organic buyers to move price, and dump. SafePump
punishes that pattern by routing buys inside a tight post-launch window into a
time-locked vesting vault.

- Snipe window: first `SNIPE_WINDOW_SLOTS = 10` slots after `initialize_curve`.
- Penalty: sniped tokens go to a `VestingVault` PDA instead of the buyer wallet.
- Lock duration: `VESTING_DURATION_SECONDS = 48 * 3600`.
- Repeat sniping: every snipe by the same wallet resets the unlock timestamp.

## Bonding curve

Virtual constant-product curve:

```text
tokens_out = vtok - ceil((vsol * vtok) / (vsol + sol_in))
sol_out    = vsol - ceil((vsol * vtok) / (vtok + tokens_in))
```

`virtual_sol_reserves` and `virtual_token_reserves` set the starting price.
`real_sol_reserves` and `real_token_reserves` track actual liquidity held by the
program.

## Instructions

- `initialize_curve(virtual_sol_reserves, virtual_token_reserves, token_supply, graduation_sol_target)`
  creates the mint, bonding curve PDA, token vault, and mints supply into the
  vault. `graduation_sol_target = 0` disables target-based completion.
- `buy(sol_amount, min_tokens_out)` buys tokens. Snipes are locked; normal buys
  go to the buyer ATA.
- `sell(token_amount, min_sol_out)` sells tokens back into the curve before
  graduation.
- `claim_vested()` lets a beneficiary claim locked tokens after the unlock time.

## Devnet setup

Install the Solana toolchain if `solana --version` or `cargo build-sbf` is not
available:

```bash
curl --proto '=https' --tlsv1.2 -sSfL https://solana-install.solana.workers.dev | bash
```

Install JS dependencies:

```bash
npm install
```

Build and test locally:

```bash
npm run build
npm test
```

Deploy to devnet:

```bash
solana config set --url devnet
solana airdrop 2
npm run deploy:devnet
```

If the public faucet is rate-limited, fund the deploy wallet with another
devnet faucet or `devnet-pow` before running the deploy command. The deploy
script uses `solana program deploy` directly with extra sign attempts because
`anchor deploy` is deprecated and can fail under devnet RPC throttling.

Verify the devnet deployment:

```bash
solana program show FMAhGG8ETyqnd4zan4HBdLRPEQvk7Cvc6kzWbsvnXj5q --url devnet
```

## Current limitations

- Graduation currently marks the curve complete, but does not yet migrate
  liquidity to Raydium. Add Raydium LaunchLab/CPMM integration before mainnet.
- Token metadata is not created yet. Add Metaplex metadata for names, symbols,
  images, and explorer compatibility.
- There is no protocol fee, creator fee, moderation layer, web frontend, indexer,
  or public API yet.
- This is suitable for devnet iteration, not unaudited mainnet use.
