# Coinbase Pro Email Validator v3.1

A robust email validation tool for checking if emails are registered on Coinbase, with advanced proxy support, DNS block bypass, and automatic fallback mechanisms.

## Features

- **DNS Block Bypass**: Automatically bypasses DNS blocking using DNS-over-HTTPS (DoH) with Cloudflare, Google DNS
- **Email Format Validation**: Validates email format, length, and checks for disposable/blocked domains
- **Coinbase Registration Check**: Tests if emails are registered on Coinbase (when network is available)
- **Test Mode**: Format validation only when network is unavailable or for testing purposes
- **Auto-Detection**: Automatically detects network unavailability and switches to test mode
- **Proxy Support**: Advanced proxy rotation with multiple format support
- **Multi-threaded**: Process multiple emails concurrently
- **Selenium Fallback**: Automatic fallback to Selenium when JavaScript challenges are detected

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python3 coin.py --input account.txt
```

### With Test Mode (Format Validation Only)

```bash
python3 coin.py --input account.txt --test-mode --no-prompt
```

### With Proxy

```bash
# Single proxy
python3 coin.py --input account.txt --proxy "host:port:user:pass"

# Multiple proxies from file
python3 coin.py --input account.txt --proxies proxies.txt
```

### Advanced Options

```bash
python3 coin.py \
  --input account.txt \
  --threads 5 \
  --retries 4 \
  --min-delay 2 \
  --max-delay 4 \
  --output-json \
  --no-prompt
```

## Command Line Options

- `--input`: Input file containing emails (default: account.txt)
- `--proxy`: Single proxy in various formats
- `--proxies`: File containing multiple proxies (one per line)
- `--threads`: Number of concurrent threads (default: 5)
- `--retries`: Number of retries per email (default: 4)
- `--min-delay`: Minimum delay between checks in seconds (default: 2)
- `--max-delay`: Maximum delay between checks in seconds (default: 4)
- `--test-mode`: Enable test mode (format validation only)
- `--no-prompt`: Skip interactive proxy prompt
- `--force-selenium`: Force Selenium-based checking
- `--requests-only`: Disable Selenium fallback
- `--output-json`: Save results to JSON file
- `--verbose`: Enable verbose logging
- `--use-doh`: Use DNS-over-HTTPS to bypass DNS blocks (enabled by default)
- `--no-dns-bypass`: Disable DNS bypass features

## Input File Format

Create a file (default: `account.txt`) with one email per line:

```
john.doe@gmail.com
jane.smith@yahoo.com
test.user@outlook.com
# Comments are supported
admin@coinbase.com
```

## Output Files

The tool generates three output files:

1. **hits.txt**: Emails that are registered on Coinbase
2. **invalid.txt**: Valid format emails that are not registered
3. **errors.txt**: Emails with invalid format or checking errors
4. **results.json**: Complete results in JSON format (with --output-json)

## Testing

Run the included test script to verify all emails are checked:

```bash
python3 test_checker.py
```

This will:
- Clean previous results
- Run the checker on all emails in account.txt
- Verify all emails were processed
- Confirm at least 20 emails were checked (requirement)

## DNS Block Bypass

The tool automatically bypasses DNS blocking using multiple techniques:

### DNS-over-HTTPS (DoH)
- Uses Cloudflare DNS (1.1.1.1)
- Falls back to Google DNS (8.8.8.8)
- Bypasses ISP/firewall DNS filtering

### How It Works
1. First attempts standard DNS resolution
2. If DNS is blocked, uses DNS-over-HTTPS to resolve domain names
3. Connects directly to resolved IP addresses

### Configuration
```bash
# DNS bypass enabled by default
python3 coin.py --input account.txt

# Disable DNS bypass if needed
python3 coin.py --input account.txt --no-dns-bypass
```

When DNS blocking is detected:
- The tool automatically tries DoH resolution
- Shows resolved IP addresses in the output
- Falls back to test mode if all methods fail

## Test Mode

When network is unavailable or `--test-mode` is specified:
- Performs email format validation only
- Checks for disposable/blocked domains
- Does not attempt to connect to Coinbase
- Useful for testing and development

The tool automatically detects network unavailability and enables test mode when needed.

## Proxy Format Support

The tool supports multiple proxy formats:

1. `host:port:username:password`
2. `host:port`
3. `protocol://username:password@host:port`
4. `protocol://host:port`

Example:
```
p1.arealproxy.com:9000:zaym246-type-residential-country-gb:fd86cea5-501a-401e-a1d4-b372c33ced0e
```

## Email Validation Rules

The tool validates emails against:
- RFC 5322 email format
- Maximum local part length (64 characters)
- Maximum domain length (255 characters)
- Disposable email domains (tempmail, guerrillamail, etc.)
- Blocked domains (qq.com, rambler.ru, etc.)
- Common typos (.con, .comm)

## Logs

All operations are logged to `coin_checker.log` for debugging purposes.

## Requirements

- Python 3.7+
- cloudscraper
- beautifulsoup4
- selenium (optional, for JavaScript challenge bypass)
- webdriver-manager (optional, for Selenium)
- tqdm

## Modified by

@LEGEND_BL - Advanced Edition v3.1
