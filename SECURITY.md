# Security Policy

## Supported Versions

We actively support security fixes for the latest released version of Moto.

| Version                | Supported                                         |
| ---------------------- | ------------------------------------------------- |
| Latest release         | Yes                                               |
| Previous major release | Security fixes considered on a case-by-case basis |
| Older releases         | No                                                |

Users are strongly encouraged to upgrade to the latest version when security vulnerabilities are discovered.

## Reporting a Vulnerability

If you believe you have discovered a security vulnerability in Moto, please **do not disclose it through a public GitHub issue, discussion, or pull request**.

Instead, please report the vulnerability privately through GitHub's **Private Vulnerability Reporting** feature, if enabled for this repository.

If private vulnerability reporting is unavailable, please contact the Moto maintainers through the security contact listed in the repository and request a private reporting channel.

Please provide as much information as possible, including:

* A clear description of the vulnerability
* The affected Moto version(s)
* The affected AWS service or component
* The affected source-code location, if known
* Steps required to reproduce the issue
* A minimal proof of concept (PoC), where possible
* The expected and actual behavior
* The potential security impact
* Any relevant CVE, CWE, or CVSS information
* Any suggested remediation, if available

Reports containing a working PoC and clear reproduction steps are especially helpful.

## Disclosure Policy

We ask security researchers to allow the maintainers reasonable time to investigate and address reported vulnerabilities before publicly disclosing technical details.

Once a vulnerability has been confirmed and a fix is available, the maintainers may publish a security advisory containing relevant information, affected versions, fixed versions, and appropriate credit to the reporter.

We will coordinate disclosure with the reporter whenever practical.

## Scope

Security reports should focus on vulnerabilities in Moto itself, including:

* Authentication or authorization flaws in Moto's mocked AWS services
* Remote code execution
* Command injection
* Server-side request forgery (SSRF)
* Path traversal
* Unsafe deserialization
* Injection vulnerabilities
* Sensitive information disclosure
* Sandbox or isolation bypasses
* Vulnerabilities that allow a malicious AWS API request to compromise the Moto server or host
* Other vulnerabilities that could affect users running Moto in development, testing, CI/CD, or shared environments

## Out of Scope

The following are generally not considered security vulnerabilities in Moto:

* Vulnerabilities that exist only in third-party dependencies and are not exploitable through Moto
* Issues requiring an already-compromised host or administrator account
* Denial-of-service issues caused solely by intentionally unreasonable resource consumption, unless they demonstrate a meaningful security impact
* Vulnerabilities in AWS itself rather than Moto's implementation
* Bugs that do not have a security impact

Dependency vulnerabilities should include evidence demonstrating that the vulnerable functionality is reachable and exploitable through Moto.

## Security Research Guidelines

Security researchers are expected to:

* Perform testing only against systems they own or have explicit authorization to test
* Avoid accessing, modifying, or deleting data belonging to other users
* Avoid actions that could disrupt infrastructure or services
* Avoid publicly disclosing vulnerabilities before coordinated disclosure
* Provide sufficient information for maintainers to reproduce the issue

## Credit

We appreciate responsible security researchers who help improve Moto's security.

With the reporter's permission, security advisories and release notes may credit researchers who responsibly disclose vulnerabilities.

## No Bug Bounty

Moto does not currently operate a bug bounty program. Submission of a security vulnerability does not imply eligibility for financial compensation.

## Contact

For security-related questions or vulnerability reports, please use GitHub's private vulnerability reporting mechanism where available.

Thank you for helping keep Moto and its users secure.
