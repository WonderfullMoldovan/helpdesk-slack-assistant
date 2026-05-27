# Password Reset Procedures

## Self-Service Password Reset

The fastest way to reset your password is via the self-service portal.

### Prerequisites

You must have previously registered your phone number or personal email for verification. If not registered, you'll need IT assistance.

### Steps

1. Navigate to https://passwordreset.company.com
2. Enter your corporate email address
3. Select verification method:
   - SMS code to registered mobile phone
   - Email to personal address
   - Security questions (if configured)
4. Enter the verification code received
5. Set new password meeting requirements (see below)

## Password Requirements

New passwords must:

- Be at least 12 characters long
- Contain at least one uppercase letter
- Contain at least one lowercase letter
- Contain at least one digit
- Contain at least one special character (!, @, #, $, %, &, *)
- Not contain your username or display name
- Not match any of your last 24 passwords
- Not be on the common password blocklist

## Password Expiration

Corporate passwords expire every 90 days. You'll receive email reminders:

- 14 days before expiration
- 7 days before expiration
- 1 day before expiration

After expiration, you'll be forced to change at next login.

## Locked Account

After 5 failed login attempts, your account locks for 30 minutes. Wait or contact IT for immediate unlock.

To request unlock:
- Slack #it-support with your username
- Verify identity via approved method
- IT will unlock manually

## Multi-Factor Authentication (MFA)

After resetting password, you may need to re-register MFA:

1. Download Microsoft Authenticator app
2. Sign in to https://mysignins.microsoft.com
3. Add account by scanning QR code
4. Verify with test code

## Common Issues

- **"Account not found"**: Use full corporate email (firstname.lastname@company.com), not username
- **"Verification code expired"**: Codes valid for 5 minutes; request new one
- **"Password doesn't meet requirements"**: Re-read requirements above carefully