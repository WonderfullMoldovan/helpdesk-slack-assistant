# VPN Connection Issues

## Common Problems

If you cannot connect to the company VPN, follow these steps in order.

### Step 1: Verify Internet Connection

Before troubleshooting VPN, ensure your internet connection works. Open a browser and try to load https://www.google.com. If this fails, the issue is with your internet, not VPN.

### Step 2: Check VPN Client Status

Open Cisco AnyConnect (Windows) or GlobalProtect (Mac). The status should show "Connected" or be ready to connect. If the client shows errors:

- **Error 433**: Authentication failed. Try logging out and back in with your corporate credentials.
- **Error 720**: Network adapter issue. Restart your computer and try again.
- **Error 691**: Incorrect credentials. Verify your username and password.

### Step 3: Restart VPN Service

If the client appears stuck:
1. Right-click the VPN icon in system tray
2. Select "Disconnect"
3. Wait 30 seconds
4. Reconnect using the same profile

### Step 4: Check Firewall

Corporate firewall may block VPN protocols. Verify with IT team that ports 443 (HTTPS) and 500/4500 (IPSec) are open on your network.

## Slow VPN Speed

If connected but slow:

- **Server location**: Try a closer server. EU users should connect to Frankfurt, US users to Virginia.
- **Split tunneling**: Enable split tunneling so only corporate traffic uses VPN (Settings > Advanced > Split Tunneling).
- **Encryption**: Switch from AES-256 to AES-128 if maximum security isn't required.

## Cannot Access Internal Resources

After VPN connects, you should access internal sites like https://internal.company.com. If not:

1. Verify VPN tunnel is "full" not "split"
2. Check that internal DNS is configured (8.8.8.8 won't work for internal sites)
3. Try accessing by IP address instead of hostname to isolate DNS issues

## Contact

If steps above don't resolve issue, contact helpdesk via Slack #it-support with your VPN client logs.