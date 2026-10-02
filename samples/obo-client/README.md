# OBO client sample

This sample signs in a user with an explicit tenant and invokes the Foundry project hosted-agent Responses endpoint. It prints the response plus trace id so the downstream audit record can show both the human user and agent identity when the gateway and agent are deployed.

Verified locally: argument parsing, token acquisition wiring, trace id generation, and Responses request shape. To verify in Azure, provide a deployed `--endpoint`, `--tenant-id`, `--client-id`, and the scope/audience used by the hosted-agent endpoint.

*Last updated: 2026-09-30*
