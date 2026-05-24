# burnBot_runCounter.py
# Local run counter that persists across script restarts

import json
import os
from datetime import datetime


class RunCounter:
    """
    Manages daily run counts for accounts, stored locally in JSON file.
    Automatically resets counts at midnight.
    """
    
    def __init__(self, storage_file="burnBot_runs.json"):
        """
        Initialize run counter with storage file.
        
        Args:
            storage_file: Path to JSON file for storing run counts
        """
        self.storage_file = storage_file
        self.data = self._load_data()
        self._cleanup_old_dates()
    
    def _load_data(self):
        """Load run count data from JSON file."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # File exists but is corrupted/empty - start fresh
                return {}
        return {}
    
    def _save_data(self):
        """Save run count data to JSON file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"[RunCounter]: WARNING - Failed to save run counts: {e}")
    
    def _cleanup_old_dates(self):
        """Remove entries older than today."""
        today = datetime.now().strftime('%Y-%m-%d')
        accounts_to_remove = []
        
        for account, account_data in self.data.items():
            if account_data.get('date') != today:
                accounts_to_remove.append(account)
        
        for account in accounts_to_remove:
            del self.data[account]
        
        if accounts_to_remove:
            self._save_data()

    def get_last_run_time(self, account):
        """
        Get the last run timestamp for an account today.
        Stored as ISO string under 'last_run_iso' in the JSON file.
        
        Args:
            account: Account username
            
        Returns:
            datetime|None: Last run time (local time) if present for today, else None
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        if account not in self.data:
            return None
        
        account_data = self.data.get(account, {})
        if account_data.get('date') != today:
            return None
        
        iso_value = account_data.get('last_run_iso')
        if not iso_value:
            return None
        
        try:
            dt = datetime.fromisoformat(str(iso_value))
            if dt.tzinfo is None:
                dt = dt.astimezone()
            return dt
        except Exception:
            return None

    def get_last_action(self, account):
        """Return the persisted last_action string for account today, or None."""
        today = datetime.now().strftime('%Y-%m-%d')
        account_data = self.data.get(account, {})
        if account_data.get('date') != today:
            return None
        return account_data.get('last_action') or None

    def set_last_run_time(self, account, run_time=None, last_action=None):
        """
        Persist the last run timestamp (and optionally last_action) for an account today.

        Args:
            account: Account username
            run_time: datetime (defaults to now)
            last_action: action label string to persist alongside the timestamp
        """
        today = datetime.now().strftime('%Y-%m-%d')
        if run_time is None:
            run_time = datetime.now().astimezone()
        elif run_time.tzinfo is None:
            run_time = run_time.astimezone()

        # Ensure account exists and is on today's date (preserve count if already tracked today)
        existing_count = 0
        existing_action = None
        if account in self.data and self.data.get(account, {}).get('date') == today:
            existing_count = int(self.data.get(account, {}).get('count', 0) or 0)
            existing_action = self.data.get(account, {}).get('last_action')

        self.data[account] = {
            'date': today,
            'count': existing_count,
            'last_run_iso': run_time.isoformat(timespec='seconds'),
            'last_action': last_action if last_action is not None else existing_action,
        }
        self._save_data()
    
    def get_run_count(self, account):
        """
        Get current run count for an account today.
        
        Args:
            account: Account username
            
        Returns:
            int: Number of runs completed today
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        if account not in self.data:
            return 0
        
        account_data = self.data[account]
        if account_data.get('date') != today:
            return 0
        
        return account_data.get('count', 0)
    
    def increment_run_count(self, account):
        """
        Increment run count for an account.
        
        Args:
            account: Account username
            
        Returns:
            int: New run count after increment
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        if account not in self.data or self.data[account].get('date') != today:
            # New day or new account - reset to 1
            self.data[account] = {
                'date': today,
                'count': 1,
                'last_run_iso': None
            }
        else:
            # Increment existing count
            self.data[account]['count'] += 1
        
        self._save_data()
        return self.data[account]['count']
    
    def reset_account(self, account):
        """
        Reset run count for a specific account.
        
        Args:
            account: Account username
        """
        if account in self.data:
            del self.data[account]
            self._save_data()
    
    def reset_all(self):
        """Reset all run counts."""
        self.data = {}
        self._save_data()
