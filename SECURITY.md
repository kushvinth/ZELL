# Security Policy

## Supported versions

ZELL is under active development. Security fixes are prioritized on the default development branch and latest releases.

## Reporting a vulnerability

Please do not open public issues for security vulnerabilities.

Instead:

- Use GitHub private vulnerability reporting for this repository, if enabled.
- Or contact maintainers directly with a detailed report.

Please include:

- Vulnerability description
- Steps to reproduce
- Potential impact
- Suggested mitigation (if available)

## Response process

We aim to:

- Acknowledge reports quickly
- Investigate and validate impact
- Release a fix or mitigation as soon as practical
- Credit responsible disclosure when appropriate

## Security best practices for operators

- Restrict CORS to trusted domains
- Put backend behind TLS and reverse proxy protections
- Keep dependencies up to date
- Use least-privilege deployment permissions
- Avoid exposing internal LLM endpoints publicly
