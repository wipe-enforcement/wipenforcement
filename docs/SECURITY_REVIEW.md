# Security checkpoint: Telegram bot identifiers

**Status: review recorded; code remediation and validation are still pending.** This document does not claim the repository is cleared of secrets.

## Finding

`qarin/operator.py` extracts Telegram bot API URLs from captured HTML into a `telegram_bot` signal. The current regex captures the entire `id:token` credential, and the signal is retained as a plain string. That is unnecessary for cross-site correlation: the bot ID is sufficient to correlate the same bot, while the token is an authentication secret. The public fixtures in `tools/qarin_selfcheck.py` and `tests/test_qarin.py` contain a realistic token-shaped sample.

The repository evidence does not establish whether the sample is synthetic or ever valid. Treat it as potentially compromised until its owner verifies otherwise. If it was real, revoke it with BotFather; deleting it from the current revision cannot invalidate it or erase it from prior Git history.

## Required code remediation

1. Extract and retain only the numeric bot ID (or a one-way fingerprint if a stronger identifier is genuinely required); never retain the token portion in `Signal`, logs, receipts, reports, or serialized outputs.
2. Replace committed credential-shaped fixtures with runtime-generated test data or a clearly non-credential fixture, and assert that output contains no token.
3. Add a regression test for extraction and output redaction, then run `python tools/qarin_selfcheck.py` and `python -m unittest discover -s tests`.
4. Scan the current tree and history as appropriate. Revoke any credential confirmed to have been real; history rewriting is separate from revocation and requires repository-owner approval.

## Deployment boundary

No collector, public snapshot, scheduled job, or production secret has been changed or deployed as part of this checkpoint. Keep the existing fail-closed publication and explicit operator-authorization gates in force until the remediation is implemented and validated.
