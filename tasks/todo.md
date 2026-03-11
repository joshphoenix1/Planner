# Gmail IMAP Integration

## Plan
Replace OAuth-based Gmail integration with simple IMAP + App Password approach.

## Tasks
- [x] Update .env with GMAIL_EMAIL and GMAIL_APP_PASSWORD placeholders
- [x] Rewrite gmail.py router to use IMAP instead of OAuth
- [x] Update frontend to remove OAuth flow, show simple status
- [x] Rebuild and test

## Review
- Removed all OAuth complexity (no Google Cloud Console needed)
- Uses standard IMAP with Gmail App Password
- Frontend shows clear setup instructions
- Filters work the same way (keywords + from addresses)
