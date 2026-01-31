# Security Policy

## Supported Versions

The following versions of PMOVES-DoX are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do NOT** create a public GitHub issue for security vulnerabilities
2. Email security concerns to the repository maintainers via GitHub private messaging
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial Assessment**: Within 1 week
- **Resolution Timeline**: Depends on severity
  - Critical: 24-72 hours
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Next scheduled release

### After Reporting

- We will work with you to understand the issue
- We will develop and test a fix
- We will credit you in the security advisory (unless you prefer anonymity)
- We will coordinate disclosure timing with you

## Security Best Practices for Users

### Environment Variables

- Never commit `.env` files with real credentials
- Use `.env.example` as a template
- Rotate credentials regularly
- Use strong, unique passwords

### Docker Deployment

- Keep Docker images updated
- Use non-root users in containers
- Limit container privileges
- Scan images for vulnerabilities

### Database

- Use strong database passwords
- Enable SSL/TLS for database connections
- Regularly backup data
- Limit database access to necessary services

### API Security

- Use HTTPS in production
- Implement rate limiting
- Validate all inputs
- Keep dependencies updated

## Known Security Considerations

### Standalone Mode

- SQLite database is stored locally
- Ensure proper file permissions on `backend/db.sqlite3`

### Docked Mode

- Credentials shared with PMOVES.AI ecosystem
- Ensure network isolation between services
- Use environment variable substitution for secrets

## Security Updates

Security updates are released as patch versions. Subscribe to repository releases to stay informed.

## Responsible Disclosure

We follow responsible disclosure practices. Please allow us reasonable time to address vulnerabilities before public disclosure.

Thank you for helping keep PMOVES-DoX secure!
