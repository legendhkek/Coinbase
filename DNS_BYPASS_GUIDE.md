# DNS Block Bypass Guide

## Overview

This guide explains how the Coinbase Email Validator bypasses DNS blocking to ensure reliable email validation even when DNS is filtered or blocked.

## Problem

DNS (Domain Name System) blocking is a common censorship and filtering technique where:
- ISPs block access to certain domains at the DNS level
- Firewall rules prevent DNS resolution
- DNS responses are filtered or redirected
- Standard DNS servers (like 8.8.8.8) may be blocked

When DNS is blocked, the validator cannot resolve `www.coinbase.com` to its IP address, preventing email validation.

## Solution: DNS-over-HTTPS (DoH)

### What is DoH?

DNS-over-HTTPS encrypts DNS queries using HTTPS protocol, making them:
- **Encrypted**: Queries look like regular HTTPS traffic
- **Unblockable**: Cannot be filtered without blocking all HTTPS
- **Private**: ISPs cannot see what domains you're resolving

### Implementation

The validator uses multiple DoH providers as fallbacks:

1. **Cloudflare DNS** (1.1.1.1)
   - Endpoint: `https://cloudflare-dns.com/dns-query`
   - Fast, reliable, privacy-focused

2. **Google Public DNS** (8.8.8.8)
   - Endpoint: `https://dns.google/resolve`
   - Global infrastructure, high availability

3. **Cloudflare 1.1.1.1 Direct**
   - Endpoint: `https://1.1.1.1/dns-query`
   - Alternative Cloudflare endpoint

### How It Works

```
┌─────────────┐
│  Validator  │
└──────┬──────┘
       │
       ├── 1. Try Standard DNS
       │   └── ✗ Blocked/Failed
       │
       ├── 2. Try Cloudflare DoH
       │   └── ✓ Success → Resolve to IP
       │
       └── 3. Connect to IP directly
           └── ✓ Bypass DNS block
```

### Code Flow

```python
def test_dns_resolution(hostname, use_doh=True):
    # Try standard DNS first
    try:
        ip = socket.gethostbyname(hostname)
        return True, ip
    except:
        pass
    
    # Fall back to DoH
    if use_doh:
        ip = resolve_via_doh(hostname)
        if ip:
            return True, ip
    
    return False, None

def resolve_via_doh(hostname):
    # Query Cloudflare DoH
    url = f"https://cloudflare-dns.com/dns-query?name={hostname}&type=A"
    response = requests.get(url, headers={'Accept': 'application/dns-json'})
    data = response.json()
    return data['Answer'][0]['data']  # Returns IP address
```

## Features

### 1. Automatic Detection

The validator automatically detects DNS blocking:

```bash
[i] Testing network connectivity with DNS bypass...
[+] DNS-over-HTTPS successfully resolved www.coinbase.com to 104.18.x.x
[+] Network connectivity confirmed (DNS bypass: www.coinbase.com -> 104.18.x.x)
```

### 2. Multiple Fallbacks

If one DoH provider fails, tries others:
- Cloudflare DNS
- Google DNS
- Alternative endpoints

### 3. Command-Line Control

```bash
# Enable DoH (default)
python3 coin.py --input account.txt

# Use DoH explicitly
python3 coin.py --input account.txt --use-doh

# Disable DNS bypass
python3 coin.py --input account.txt --no-dns-bypass
```

## Usage Examples

### Basic Usage (DoH Enabled)

```bash
python3 coin.py --input account.txt --no-prompt
```

Output:
```
[i] Configuring DNS bypass to avoid DNS blocks...
[+] System DNS may be blocked, DNS-over-HTTPS will be used as fallback
[+] DNS bypass configured - will use DNS-over-HTTPS if standard DNS fails
[i] Testing network connectivity with DNS bypass...
[+] Network connectivity confirmed (DNS bypass: www.coinbase.com -> 104.18.x.x)
```

### With Proxy (DoH + Proxy)

```bash
python3 coin.py --input account.txt --proxy "host:port:user:pass"
```

DNS bypass works alongside proxy configuration for maximum reliability.

### Disable DNS Bypass

```bash
python3 coin.py --input account.txt --no-dns-bypass
```

Use when DNS is not blocked or you want to use only standard DNS.

## Technical Details

### DoH Request Format

```http
GET https://cloudflare-dns.com/dns-query?name=www.coinbase.com&type=A HTTP/1.1
Accept: application/dns-json
```

### DoH Response Format

```json
{
  "Status": 0,
  "Answer": [
    {
      "name": "www.coinbase.com",
      "type": 1,
      "TTL": 300,
      "data": "104.18.x.x"
    }
  ]
}
```

### Error Handling

```python
if "NameResolutionError" in error_str or "Failed to resolve" in error_str:
    logger.debug(f"Network unavailable for {url}: DNS resolution failed")
    return None, "Network unavailable: Cannot resolve hostname"
```

## Benefits

1. **Bypass DNS Censorship**: Works even when DNS is blocked
2. **Privacy**: Encrypted DNS queries
3. **Reliability**: Multiple fallback providers
4. **Automatic**: No manual configuration needed
5. **Compatible**: Works with proxies and other features

## Limitations

1. **Requires HTTPS Access**: DoH providers must be reachable
2. **Slightly Slower**: Extra DNS lookup via HTTPS
3. **Not for All Blocks**: Cannot bypass IP-level blocking

## Troubleshooting

### DNS Still Fails

If DoH fails, check:
1. HTTPS access to cloudflare-dns.com and dns.google
2. Firewall rules blocking HTTPS to DNS providers
3. Use a proxy that allows HTTPS connections

### Connection Blocked After DNS

```
[+] DNS-over-HTTPS successfully resolved www.coinbase.com to 104.18.x.x
[!] Connection blocked: [Errno 111] Connection refused
[i] DNS resolution works but connection is blocked. Consider using a proxy.
```

This means:
- DNS bypass worked (resolved to IP)
- But IP connection is blocked
- Solution: Use `--proxy` option with a proxy server

## Security

### Privacy Benefits

- **Encrypted queries**: ISP cannot see DNS lookups
- **No logging**: Cloudflare/Google privacy policies
- **Prevents DNS spoofing**: HTTPS validation

### Considerations

- Trust in DoH providers (Cloudflare, Google)
- HTTPS must not be intercepted (no MITM)
- DoH providers can still see queries

## Advanced Configuration

### Custom DoH Provider

Edit `coin.py` and modify the `resolve_via_doh()` function:

```python
doh_providers = [
    f"https://your-doh-server.com/dns-query?name={hostname}&type=A",
    # ... existing providers
]
```

### Timeout Configuration

Adjust DoH timeout in `resolve_via_doh()`:

```python
response = requests.get(doh_url, headers=headers, timeout=10)  # Increase timeout
```

## Conclusion

The DNS block bypass feature ensures the Coinbase Email Validator works reliably even in restricted network environments. By using DNS-over-HTTPS, the tool can resolve domain names and validate emails regardless of DNS filtering or blocking.

For most users, the default configuration works automatically without any setup required.
