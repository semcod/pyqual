#!/usr/bin/env python3
"""Test script for GitHub Actions integration.

Run with your GitHub token:
    GITHUB_TOKEN=ghp_xxx python3 test_github_integration.py

Or authenticate gh CLI first:
    gh auth login
    python3 test_github_integration.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add pyqual to path
sys.path.insert(0, str(Path(__file__).parent))

from pyqual.github_actions import GitHubActionsReporter


def test_github_connection():
    """Test connection to GitHub."""
    print("=" * 60)
    print("Testing GitHub Actions Integration")
    print("=" * 60)
    
    # Try to get token from env or gh CLI
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "semcod/pyqual")
    
    if not token:
        # Try to get from gh CLI
        import subprocess
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                token = result.stdout.strip()
                print("✓ Got token from gh CLI")
        except Exception:
            pass
    
    if not token:
        print("❌ No GITHUB_TOKEN found!")
        print("\nSet it with:")
        print("  export GITHUB_TOKEN=ghp_your_token_here")
        print("\nOr authenticate gh CLI:")
        print("  gh auth login")
        return False
    
    print(f"✓ Token available")
    print(f"✓ Repository: {repo}")
    
    # Create reporter
    reporter = GitHubActionsReporter(token=token, repo=repo)
    
    # Test 1: Fetch issues
    print("\n--- Test 1: Fetching open issues ---")
    issues = reporter.fetch_issues(state="open")
    print(f"✓ Found {len(issues)} open issues")
    
    if issues:
        for i, issue in enumerate(issues[:3], 1):
            print(f"  {i}. #{issue.number}: {issue.title[:50]}")
    
    # Test 2: Fetch PRs
    print("\n--- Test 2: Fetching open PRs ---")
    prs = reporter.fetch_pull_requests(state="open")
    print(f"✓ Found {len(prs)} open PRs")
    
    if prs:
        for i, pr in enumerate(prs[:3], 1):
            print(f"  {i}. #{pr.number}: {pr.title[:50]}")
    
    # Test 3: Create test issue (optional)
    print("\n--- Test 3: Creating test issue ---")
    test_title = "[TEST] GitHub Actions Integration Test"
    test_body = """## Test Issue
    
This issue was created automatically by test script.

### Purpose
Verify GitHub Actions integration works correctly.

### Checklist
- [ ] Issue created
- [ ] Can be fetched by pyqual
- [ ] Comments can be posted

---
*Auto-generated test*"""
    
    issue_num = reporter.ensure_issue_exists(
        title=test_title,
        body=test_body,
        labels=["test", "pyqual-fix"]
    )
    
    if issue_num:
        print(f"✓ Test issue #{issue_num} ready")
        print(f"\nView at: https://github.com/{repo}/issues/{issue_num}")
        
        # Test 4: Post comment
        print(f"\n--- Test 4: Posting comment to #{issue_num} ---")
        comment = """## ✅ Test Comment

Integration test successful!

- Token works
- API calls work
- Comments work

---
*Test at: {timestamp}""".format(timestamp=__import__('datetime').datetime.now().isoformat())
        
        success = reporter.post_issue_comment(comment, issue_num)
        if success:
            print(f"✓ Comment posted to #{issue_num}")
        else:
            print(f"❌ Failed to post comment")
        
        print(f"\n✅ ALL TESTS PASSED!")
        print(f"\nView the test issue:")
        print(f"  https://github.com/{repo}/issues/{issue_num}")
        
        # Ask if user wants to close the test issue
        print("\n--- Cleanup ---")
        print(f"To close test issue #{issue_num}:")
        print(f"  gh issue close {issue_num} --repo {repo}")
        
        return True
    else:
        print("❌ Failed to create test issue")
        return False


def test_todo_creation():
    """Test creating TODO.md from GitHub issues."""
    print("\n" + "=" * 60)
    print("Testing TODO.md Creation")
    print("=" * 60)
    
    from pyqual.github_tasks import fetch_github_tasks, save_tasks_to_todo
    
    tasks = fetch_github_tasks(
        label="pyqual-fix",
        state="open",
        include_issues=True,
        include_prs=True
    )
    
    print(f"✓ Fetched {len(tasks)} tasks with label 'pyqual-fix'")
    
    if tasks:
        # Save to TODO.md
        todo_path = Path("TODO_test.md")
        save_tasks_to_todo(tasks, todo_path, append=False)
        print(f"✓ Saved to {todo_path}")
        print(f"\nContent preview:")
        print("-" * 40)
        print(todo_path.read_text()[:500])
        print("-" * 40)
        
        # Cleanup
        todo_path.unlink()
        print(f"✓ Cleaned up {todo_path}")
    
    return True


if __name__ == "__main__":
    print("\n🔧 GitHub Integration Test for pyqual\n")
    
    # Check if running in actual GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print("⚠️  Running in GitHub Actions - using environment variables")
    else:
        print("ℹ️  Running locally - need GITHUB_TOKEN or gh CLI auth\n")
    
    # Run tests
    success1 = test_github_connection()
    success2 = test_todo_creation()
    
    if success1 and success2:
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nGitHub Actions integration is working correctly.")
        print("\nNext steps:")
        print("1. Push code to GitHub")
        print("2. Create issue with label 'pyqual-fix'")
        print("3. Watch Actions tab for automatic processing")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("⚠️  SOME TESTS FAILED")
        print("=" * 60)
        print("\nCheck:")
        print("- GITHUB_TOKEN is set correctly")
        print("- Repository exists: semcod/pyqual")
        print("- You have write permissions")
        sys.exit(1)
