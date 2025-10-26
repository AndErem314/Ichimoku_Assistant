"""
Scheduler for Live Monitoring

Schedules analysis tasks to run at specific times every 4 hours.
Runs at 00:00:15, 04:00:15, 08:00:15, 12:00:15, 16:00:15, 20:00:15 UTC.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


def _next_4h_boundary_utc(now: datetime) -> datetime:
    """Compute the next 4h boundary in UTC at :00:15 seconds.

    Example boundaries (UTC): 00:00:15, 04:00:15, 08:00:15, 12:00:15, 16:00:15, 20:00:15
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    # Base candidate at the current hour with minute=0, second=15
    candidate = now.replace(minute=0, second=15, microsecond=0)

    # Hours since last 4h boundary
    offset_hours = candidate.hour % 4
    if offset_hours != 0:
        candidate = candidate + timedelta(hours=(4 - offset_hours))

    # If we already passed the :00:15 mark this cycle, jump to the next one
    if candidate <= now:
        candidate = candidate + timedelta(hours=4)

    return candidate


class MonitorScheduler:
    """
    Scheduler for crypto trading monitor.

    Runs analysis at 15 seconds past each 4-hour mark to ensure
    complete candles are available for analysis.

    Schedule (UTC): 00:00:15, 04:00:15, 08:00:15, 12:00:15, 16:00:15, 20:00:15
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
        self._next_run_utc: Optional[datetime] = None

        logger.info("Initialized MonitorScheduler")

    def _run_with_logging(self):
        """Wrapper to run analysis with logging."""
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting scheduled analysis at {start_time.isoformat()}")

        try:
            self.analysis_function()
            end_time = datetime.now(timezone.utc)
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

        if run_immediately:
            self.run_immediately()

        self.is_running = True
        logger.info("Scheduler started, entering main loop (UTC-aligned 4h schedule)")

        # Initialize next run strictly in UTC
        self._next_run_utc = _next_4h_boundary_utc(datetime.now(timezone.utc))
        logger.info(f"Next run scheduled at {self._next_run_utc.isoformat()} (UTC)")

        while self.is_running:
            try:
                now = datetime.now(timezone.utc)
                if self._next_run_utc and now >= self._next_run_utc:
                    self._run_with_logging()
                    # Compute the subsequent run
                    self._next_run_utc = _next_4h_boundary_utc(datetime.now(timezone.utc))
                    logger.info(f"Next run scheduled at {self._next_run_utc.isoformat()} (UTC)")
                # Sleep a short time to avoid drift; wake up frequently near boundary
                sleep_seconds = max(5, min(60, int((self._next_run_utc - now).total_seconds() - 1))) if self._next_run_utc else 30
                time.sleep(sleep_seconds)
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in scheduler main loop: {e}", exc_info=True)
                time.sleep(30)

    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler")
        self.is_running = False
        self._next_run_utc = None

    def get_next_run(self) -> Optional[datetime]:
        """
        Get the next scheduled run time (UTC).
        """
        return self._next_run_utc

    def get_schedule_info(self) -> dict:
        """
        Get information about the current schedule.
        """
        next_run = self.get_next_run()
        return {
            'is_running': self.is_running,
            'num_jobs': 1 if self.is_running else 0,
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
