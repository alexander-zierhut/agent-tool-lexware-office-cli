# agent-tool-lexware-cli

Agent-ready CLI for **Lexware Office** — contacts, invoices, and the
receivables/AR-aging the API refuses to total for you. `lexware-cli guide`.

Contributing: `pip install -e '.[test]' && pytest` (hermetic tests need no account).
The integration tests boot the sibling `lexware-office-mock` as their backend.
