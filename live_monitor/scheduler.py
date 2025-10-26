"""
Scheduler for Live Monitoring

Schedules analysis tasks to run at specific times every 4 hours.
Runs at 00:01, 04:01, 08:01, 12:01, 16:01, 20:01 UTC.
"""

import schedule
import time
from datetime import datetime
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """
    Scheduler for crypto trading monitor.
    
    Runs analysis at 15 seconds past each 4-hour mark to ensure
    complete candles are available for analysis.
    
    Schedule: 00:00:15, 04:00:15, 08:00:15, 12:00:15, 16:00:15, 20:00:15 UTC
    """
    
    def __init__(self, analysis_function: Callable):
        """
        Initialize scheduler.
        
        Args:
            analysis_function: Function to call on each schedule run
                             Should handle its own exceptions
        """
        self.analysis_function = analysis_function
        self.is_running = False
        
        logger.info("Initialized MonitorScheduler")
    
    def setup_schedule(self):
        """Setup the schedule for 4-hour intervals at :00:15 mark."""
        # Clear any existing jobs
        schedule.clear()
        
        # Schedule at :00:15 (15 seconds) past each 4-hour mark
        schedule_times = ["00:00:15", "04:00:15", "08:00:15", "12:00:15", "16:00:15", "20:00:15"]
        
        for time_str in schedule_times:
            schedule.every().day.at(time_str).do(self._run_with_logging)
            logger.info(f"Scheduled analysis at {time_str} UTC")
        
        logger.info(f"Setup complete: {len(schedule_times)} scheduled runs per day")
    
    def _run_with_logging(self):
        """Wrapper to run analysis with logging."""
        start_time = datetime.utcnow()
        logger.info(f"Starting scheduled analysis at {start_time.isoformat()}")
        
        try:
            self.analysis_function()
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Completed scheduled analysis in {duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Error in scheduled analysis: {e}", exc_info=True)
            # Don't raise - allow scheduler to continue
    
    def run_immediately(self):
        """Run analysis immediately (useful for startup)."""
        logger.info("Running immediate analysis on startup")
        self._run_with_logging()
    
    def start(self, run_immediately: bool = True):
        """
        Start the scheduler.
        
        Args:
            run_immediately: If True, run analysis immediately on start
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.setup_schedule()
        
        if run_immediately:
            self.run_immediately()
        
        self.is_running = True
        logger.info("Scheduler started, entering main loop")
        
        # Main loop
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in scheduler main loop: {e}", exc_info=True)
                # Continue running despite errors
                time.sleep(60)
    
    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler")
        self.is_running = False
        schedule.clear()
    
    def get_next_run(self) -> Optional[datetime]:
        """
        Get the next scheduled run time.
        
        Returns:
            DateTime of next scheduled run, or None if no jobs scheduled
        """
        jobs = schedule.get_jobs()
        if not jobs:
            return None
        
        # Get the next run time from schedule
        next_run = schedule.next_run()
        return next_run
    
    def get_schedule_info(self) -> dict:
        """
        Get information about the current schedule.
        
        Returns:
            Dictionary with schedule information
        """
        jobs = schedule.get_jobs()
        next_run = self.get_next_run()
        
        return {
            'is_running': self.is_running,
            'num_jobs': len(jobs),
            'next_run': next_run.isoformat() if next_run else None,
            'schedule_times': ["00:00:15", "04:00:15", "08:00:15", "12:00:15", "16:00:15", "20:00:15"],
            'timezone': 'UTC'
        }


class OneTimeScheduler:
    """
    Simple one-time scheduler for testing.
    Runs analysis once and exits.
    """
    
    def __init__(self, analysis_function: Callable):
        """
        Initialize one-time scheduler.
        
        Args:
            analysis_function: Function to call
        """
        self.analysis_function = analysis_function
        logger.info("Initialized OneTimeScheduler (test mode)")
    
    def start(self):
        """Run analysis once and exit."""
        logger.info("Running one-time analysis")
        
        try:
            self.analysis_function()
            logger.info("One-time analysis completed successfully")
        except Exception as e:
            logger.error(f"Error in one-time analysis: {e}", exc_info=True)
            raise
