# Batch Processing Guide - 100-200+ Emails

This guide explains how to efficiently process large batches of 100-200+ email addresses using the Coinbase Email Validator.

## Overview

The validator has been optimized for large-scale batch processing with:
- **Resume Capability**: Skip already checked emails
- **Batch Processing**: Split large datasets into manageable chunks
- **Progress Tracking**: Real-time ETA and progress checkpoints
- **Detailed Reports**: Summary statistics for large batches

## Quick Start

### Processing 100-200 Emails

```bash
# Fast processing with batch mode
python3 coin.py \
  --input account_large.txt \
  --threads 15 \
  --batch-size 50 \
  --save-progress \
  --min-delay 0.5 \
  --max-delay 1.5 \
  --no-prompt
```

### Resume Interrupted Processing

```bash
# Continue from where you left off
python3 coin.py \
  --input account_large.txt \
  --resume \
  --threads 15 \
  --no-prompt
```

## Command-Line Options

### Batch Processing Options

| Option | Description | Recommended Value |
|--------|-------------|-------------------|
| `--batch-size N` | Process emails in batches of N | 50-100 for large lists |
| `--resume` | Skip already checked emails | Always use for interrupted runs |
| `--save-progress` | Save checkpoints periodically | Use for 200+ emails |
| `--threads N` | Number of concurrent threads | 10-20 for large batches |
| `--min-delay` | Minimum delay between checks (seconds) | 0.5-1.0 for test mode |
| `--max-delay` | Maximum delay between checks (seconds) | 1.0-2.0 for test mode |

## Performance Guidelines

### Optimal Settings by Dataset Size

#### 50-100 Emails
```bash
python3 coin.py --input emails.txt \
  --threads 10 \
  --min-delay 1 \
  --max-delay 2 \
  --no-prompt
```
- Expected time: ~2-3 minutes
- No batching needed

#### 100-200 Emails
```bash
python3 coin.py --input emails.txt \
  --threads 15 \
  --batch-size 50 \
  --save-progress \
  --min-delay 0.5 \
  --max-delay 1.5 \
  --no-prompt
```
- Expected time: ~3-5 minutes
- Batch size: 50
- Progress saving recommended

#### 200-500 Emails
```bash
python3 coin.py --input emails.txt \
  --threads 20 \
  --batch-size 100 \
  --save-progress \
  --min-delay 0.5 \
  --max-delay 1.0 \
  --no-prompt
```
- Expected time: ~8-15 minutes
- Batch size: 100
- Progress saving required

#### 500+ Emails
```bash
python3 coin.py --input emails.txt \
  --threads 20 \
  --batch-size 100 \
  --resume \
  --save-progress \
  --min-delay 0.3 \
  --max-delay 0.8 \
  --no-prompt
```
- Expected time: 15+ minutes
- Batch size: 100
- Always use resume capability

## Features Explained

### 1. Batch Processing

**What it does:**
Splits your email list into smaller batches and processes them sequentially.

**Why use it:**
- Better memory management for large lists
- Progress tracking between batches
- Easier to recover from interruptions

**Example:**
```bash
--batch-size 50  # Process 50 emails at a time
```

Output shows:
```
[+] Processing batch 1/3 (50 emails)
[i] Progress: 0/149 emails checked
[+] Processing batch 2/3 (50 emails)
[i] Progress: 50/149 emails checked
[i] Estimated time remaining: 12s
```

### 2. Resume Capability

**What it does:**
Automatically skips emails that have already been checked by reading existing output files (hits.txt, invalid.txt, errors.txt).

**Why use it:**
- Recover from interruptions without reprocessing
- Save time when adding new emails to existing list
- Useful for iterative processing

**Example:**
```bash
--resume  # Skip already checked emails
```

Output shows:
```
[i] Resume mode: Checking for previously processed emails...
[+] Skipping 148 already checked emails
[+] 1 emails remaining to check
```

### 3. Progress Saving

**What it does:**
Saves a checkpoint file (progress.json) after each batch with details about checked emails.

**Why use it:**
- Track progress across sessions
- Recover batch state after interruption
- Monitor processing statistics

**Example:**
```bash
--save-progress  # Save progress after each batch
```

Creates `progress.json`:
```json
{
  "checked_emails": ["email1@...", "email2@..."],
  "total_checked": 100,
  "batches_completed": 2,
  "last_update": "2025-11-16T10:00:00"
}
```

### 4. Progress Tracking

**Real-time ETA:**
The system estimates completion time based on current processing rate.

```
[+] Processing batch 2/3 (50 emails)
[i] Progress: 50/149 emails checked
[i] Estimated time remaining: 12s
```

**Summary Report:**
For batches with 50+ emails, a detailed report is generated:

```
╔════════════════════════════════════════════════════════════════╗
║                    BATCH PROCESSING SUMMARY                    ║
╚════════════════════════════════════════════════════════════════╝

Total Emails Processed:        149
Processing Time:            21.71s
Average Rate:               6.86 emails/sec

┌────────────────────────────────────────────────────────────────┐
│ FORMAT VALIDATION                                              │
├────────────────────────────────────────────────────────────────┤
│ Valid Format:                141 (94.6%)                       │
│ Invalid Format:                8 (5.4%)                        │
└────────────────────────────────────────────────────────────────┘
```

## Best Practices

### 1. Thread Count
- **Default (5 threads)**: Good for small lists, slow networks
- **10-15 threads**: Optimal for 100-200 emails
- **15-20 threads**: Best for 200+ emails
- **20+ threads**: May hit rate limits without proxies

### 2. Delays
- **Test Mode**: Use lower delays (0.3-1.5s) - no network calls
- **Live Checking**: Use higher delays (1.5-4s) - avoid rate limits
- **With Proxies**: Can use lower delays (0.5-2s)

### 3. Batch Sizes
- **50 emails**: Good balance for most cases
- **100 emails**: Better for very large datasets (500+)
- **No batching (0)**: Use only for small lists (<50)

### 4. When to Use Resume
- Always use when continuing interrupted processing
- Use when adding new emails to an existing list
- Use after errors or network issues
- Safe to use anytime - skips already processed emails

## Workflow Examples

### Example 1: First-Time Large Batch

```bash
# Step 1: Process with batching and progress saving
python3 coin.py \
  --input my_emails.txt \
  --threads 15 \
  --batch-size 50 \
  --save-progress \
  --output-json \
  --no-prompt

# Results:
# - hits.txt: Registered emails
# - invalid.txt: Not registered emails
# - errors.txt: Invalid format emails
# - results.json: Complete JSON output
# - progress.json: Progress checkpoint
```

### Example 2: Interrupted Processing

```bash
# Step 1: Original command (interrupted)
python3 coin.py --input emails.txt --threads 15 --batch-size 50 --no-prompt
# ^C (interrupted at 50%)

# Step 2: Resume from where you left off
python3 coin.py --input emails.txt --resume --threads 15 --no-prompt
# [+] Skipping 75 already checked emails
# [+] 75 emails remaining to check
```

### Example 3: Adding New Emails

```bash
# Step 1: Process initial list
python3 coin.py --input emails_v1.txt --threads 15 --no-prompt

# Step 2: Add more emails to file
cat new_emails.txt >> emails_v1.txt

# Step 3: Process only new emails
python3 coin.py --input emails_v1.txt --resume --threads 15 --no-prompt
# Automatically skips old emails, processes only new ones
```

## Troubleshooting

### Issue: Processing Too Slow

**Solution:**
```bash
# Increase threads and use batching
python3 coin.py --input emails.txt --threads 20 --batch-size 100 --no-prompt
```

### Issue: Running Out of Memory

**Solution:**
```bash
# Use smaller batch sizes
python3 coin.py --input emails.txt --batch-size 25 --no-prompt
```

### Issue: Rate Limited

**Solution:**
```bash
# Increase delays and use fewer threads
python3 coin.py --input emails.txt --threads 5 --min-delay 3 --max-delay 5 --no-prompt
```

### Issue: Process Interrupted

**Solution:**
```bash
# Just add --resume flag
python3 coin.py --input emails.txt --resume --no-prompt
```

## Performance Benchmarks

Based on testing with account_large.txt (149 emails):

| Configuration | Time | Rate | Notes |
|--------------|------|------|-------|
| Default (5 threads) | ~30s | ~5 emails/sec | Good for small batches |
| 10 threads, batch-size 50 | ~22s | ~6.8 emails/sec | Optimal for 100-200 |
| 15 threads, batch-size 50 | ~18s | ~8.3 emails/sec | Best for 200+ |
| 20 threads, batch-size 100 | ~15s | ~9.9 emails/sec | Maximum speed |

*Note: Times are for test mode. Live checking will be slower due to network latency.*

## Output Files

All output files are appended (not overwritten):

- **hits.txt**: One email per line - registered on Coinbase
- **invalid.txt**: One email per line - not registered
- **errors.txt**: Email | Error message - validation failures
- **results.json**: Complete JSON array of all results (if --output-json)
- **progress.json**: Progress checkpoint (if --save-progress)

## Tips for Very Large Batches (1000+ Emails)

1. **Use Test Mode First**: Validate email formats without network calls
   ```bash
   python3 coin.py --input huge_list.txt --test-mode --threads 20 --batch-size 100
   ```

2. **Process in Stages**: Split your list into multiple files
   ```bash
   split -l 500 huge_list.txt batch_
   # Process each batch_* file separately
   ```

3. **Use Progress Saving**: Essential for recovery
   ```bash
   --save-progress
   ```

4. **Monitor Resources**: Check system resources during processing
   ```bash
   # Run in separate terminal
   watch -n 1 'ps aux | grep coin.py'
   ```

5. **Consider Proxies**: For live checking, use proxy rotation
   ```bash
   --proxies proxy_list.txt
   ```

## Conclusion

The Coinbase Email Validator is optimized for processing 100-200+ emails efficiently. Use batch processing, resume capability, and progress tracking for best results with large datasets.

For questions or issues, refer to the main README.md and DNS_BYPASS_GUIDE.md.
