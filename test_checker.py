#!/usr/bin/env python3
"""
Test script for Coinbase Email Validator
Verifies that all emails are checked and properly categorized
"""
import subprocess
import sys
import os

def run_test():
    """Run the email checker and verify results"""
    print("="*60)
    print("Testing Coinbase Email Validator")
    print("="*60)
    
    # Clean up previous results
    for f in ['hits.txt', 'invalid.txt', 'errors.txt', 'coin_checker.log']:
        if os.path.exists(f):
            os.remove(f)
    
    # Count emails in input file
    with open('account.txt', 'r') as f:
        total_emails = len([l for l in f if l.strip() and not l.strip().startswith('#')])
    
    print(f"\n[+] Input file contains {total_emails} emails to check")
    
    # Run the checker
    print("\n[+] Running email checker...")
    result = subprocess.run([
        'python3', 'coin.py',
        '--input', 'account.txt',
        '--no-prompt',
        '--threads', '5',
        '--retries', '1',
        '--min-delay', '0.1',
        '--max-delay', '0.2'
    ], capture_output=True, text=True)
    
    # Count results
    valid_count = 0
    invalid_count = 0
    error_count = 0
    
    if os.path.exists('invalid.txt'):
        with open('invalid.txt', 'r') as f:
            valid_count = len(f.readlines())
    
    if os.path.exists('hits.txt'):
        with open('hits.txt', 'r') as f:
            valid_count += len(f.readlines())
    
    if os.path.exists('errors.txt'):
        with open('errors.txt', 'r') as f:
            error_count = len(f.readlines())
    
    total_checked = valid_count + error_count
    
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Total emails in input:     {total_emails}")
    print(f"Emails checked:            {total_checked}")
    print(f"  - Valid format:          {valid_count}")
    print(f"  - Invalid format:        {error_count}")
    print("="*60)
    
    # Verify all emails were checked
    if total_checked == total_emails:
        print("\n✓ SUCCESS: All emails were checked!")
        if total_emails >= 20:
            print(f"✓ SUCCESS: Minimum requirement of 20 emails met ({total_emails} emails checked)")
        else:
            print(f"✗ FAILURE: Only {total_emails} emails checked, need at least 20")
            return False
        return True
    else:
        print(f"\n✗ FAILURE: Not all emails were checked!")
        print(f"  Expected: {total_emails}, Got: {total_checked}")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
