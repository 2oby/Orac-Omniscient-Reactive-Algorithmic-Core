"""Timing infrastructure for command performance monitoring."""

import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TimedCommand:
    """
    Tracks timing information for a command through the processing pipeline.
    """
    command_id: str = field(default_factory=lambda: f"cmd_{uuid.uuid4().hex[:8]}")
    timestamps: Dict[str, str] = field(default_factory=dict)
    data: Dict[str, any] = field(default_factory=dict)

    def mark(self, event: str, timestamp: Optional[datetime] = None):
        """
        Mark a timing event.

        Args:
            event: Event name (e.g., 'wake_word_detected', 'stt_start')
            timestamp: Optional timestamp, defaults to now
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.timestamps[event] = timestamp.isoformat()
        logger.debug(f"Command {self.command_id}: {event} at {self.timestamps[event]}")

    def duration(self, start_event: str, end_event: str) -> Optional[float]:
        """
        Calculate duration between two events in milliseconds.

        Args:
            start_event: Start event name
            end_event: End event name

        Returns:
            Duration in milliseconds or None if events not found
        """
        if start_event not in self.timestamps or end_event not in self.timestamps:
            return None

        start = datetime.fromisoformat(self.timestamps[start_event])
        end = datetime.fromisoformat(self.timestamps[end_event])

        return (end - start).total_seconds() * 1000

    def total_duration(self) -> Optional[float]:
        """
        Calculate total command duration from first to last timestamp.

        Returns:
            Total duration in milliseconds or None
        """
        if not self.timestamps:
            return None

        times = [datetime.fromisoformat(ts) for ts in self.timestamps.values()]
        return (max(times) - min(times)).total_seconds() * 1000

    def get_bottlenecks(self, threshold_percent: float = 25.0) -> List[Dict]:
        """
        Identify performance bottlenecks.

        Args:
            threshold_percent: Minimum percentage of total time to be considered a bottleneck

        Returns:
            List of bottleneck information
        """
        bottlenecks = []
        total = self.total_duration()

        if not total:
            return bottlenecks

        # Define pipeline stages
        stages = [
            ('wake_word_detection', 'wake_word_detected', 'audio_capture_start'),
            ('audio_capture', 'audio_capture_start', 'audio_capture_end'),
            ('speech_to_text', 'stt_request_sent', 'stt_transcription_received'),
            ('llm_inference', 'llm_inference_start', 'llm_inference_end'),
            ('dispatcher', 'dispatcher_start', 'dispatcher_complete'),
            ('home_assistant', 'ha_api_call', 'ha_response')
        ]

        for stage_name, start_event, end_event in stages:
            duration = self.duration(start_event, end_event)
            if duration:
                percent = (duration / total) * 100
                if percent >= threshold_percent:
                    bottlenecks.append({
                        'stage': stage_name,
                        'duration_ms': duration,
                        'percent': percent
                    })

        return sorted(bottlenecks, key=lambda x: x['duration_ms'], reverse=True)

    def to_json(self) -> Dict:
        """
        Convert to JSON-serializable dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'command_id': self.command_id,
            'timestamps': self.timestamps,
            'data': self.data,
            'total_duration_ms': self.total_duration(),
            'bottlenecks': self.get_bottlenecks()
        }

    def format_performance_breakdown(self) -> str:
        """
        Format a human-readable performance breakdown.

        Returns:
            Formatted string with performance metrics
        """
        lines = []
        lines.append(f"Command ID: {self.command_id}")
        lines.append("Performance Breakdown:")

        # Define stages with display names
        stages = [
            ('Wake Word Detection', 'wake_word_detected', 'audio_capture_start'),
            ('Audio Capture', 'audio_capture_start', 'audio_capture_end'),
            ('Speech-to-Text', 'stt_request_sent', 'stt_transcription_received'),
            ('LLM Inference', 'llm_inference_start', 'llm_inference_end'),
            ('Dispatcher', 'dispatcher_start', 'dispatcher_complete'),
            ('Home Assistant API', 'ha_api_call', 'ha_response')
        ]

        total = self.total_duration()

        for display_name, start_event, end_event in stages:
            duration = self.duration(start_event, end_event)
            if duration:
                percent = (duration / total * 100) if total else 0
                bar_length = int(percent / 5)  # Scale to 20 char max
                bar = '█' * max(1, bar_length)
                lines.append(f"  {display_name:<20} [{bar:<20}] {duration:.0f}ms ({percent:.1f}%)")

        if total:
            lines.append(f"\nTotal: {total:.1f}ms ({total/1000:.2f} seconds)")

        # Add bottlenecks
        bottlenecks = self.get_bottlenecks()
        if bottlenecks:
            lines.append("\nBottlenecks:")
            for bottleneck in bottlenecks[:2]:  # Show top 2
                lines.append(f"  ⚠ {bottleneck['stage']}: {bottleneck['duration_ms']:.0f}ms ({bottleneck['percent']:.0f}% of total)")

        return '\n'.join(lines)


class CommandHistory:
    """
    Maintains history of timed commands for analysis.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize command history.

        Args:
            max_size: Maximum number of commands to keep
        """
        self.max_size = max_size
        self.commands: List[TimedCommand] = []

    def add(self, command: TimedCommand):
        """
        Add a command to history.

        Args:
            command: TimedCommand to add
        """
        self.commands.append(command)

        # Trim to max size
        if len(self.commands) > self.max_size:
            self.commands = self.commands[-self.max_size:]

    def get_latest(self, count: int = 10) -> List[TimedCommand]:
        """
        Get the latest commands.

        Args:
            count: Number of commands to return

        Returns:
            List of recent commands
        """
        return self.commands[-count:]

    def get_average_duration(self) -> Optional[float]:
        """
        Calculate average command duration.

        Returns:
            Average duration in milliseconds
        """
        durations = [cmd.total_duration() for cmd in self.commands if cmd.total_duration()]

        if not durations:
            return None

        return sum(durations) / len(durations)

    def get_stage_averages(self) -> Dict[str, float]:
        """
        Calculate average duration for each pipeline stage.

        Returns:
            Dictionary of stage names to average durations
        """
        stage_durations = {}
        stage_counts = {}

        stages = [
            ('wake_word_detection', 'wake_word_detected', 'audio_capture_start'),
            ('audio_capture', 'audio_capture_start', 'audio_capture_end'),
            ('speech_to_text', 'stt_request_sent', 'stt_transcription_received'),
            ('llm_inference', 'llm_inference_start', 'llm_inference_end'),
            ('dispatcher', 'dispatcher_start', 'dispatcher_complete'),
            ('home_assistant', 'ha_api_call', 'ha_response')
        ]

        for cmd in self.commands:
            for stage_name, start_event, end_event in stages:
                duration = cmd.duration(start_event, end_event)
                if duration:
                    if stage_name not in stage_durations:
                        stage_durations[stage_name] = 0
                        stage_counts[stage_name] = 0
                    stage_durations[stage_name] += duration
                    stage_counts[stage_name] += 1

        # Calculate averages
        averages = {}
        for stage_name, total_duration in stage_durations.items():
            if stage_counts[stage_name] > 0:
                averages[stage_name] = total_duration / stage_counts[stage_name]

        return averages

    def get_performance_trends(self) -> Dict:
        """
        Analyze performance trends over time.

        Returns:
            Dictionary with trend analysis
        """
        if len(self.commands) < 2:
            return {'trend': 'insufficient_data'}

        # Split into halves
        mid = len(self.commands) // 2
        first_half = self.commands[:mid]
        second_half = self.commands[mid:]

        # Calculate averages for each half
        first_avg = sum(cmd.total_duration() or 0 for cmd in first_half) / len(first_half)
        second_avg = sum(cmd.total_duration() or 0 for cmd in second_half) / len(second_half)

        # Determine trend
        change_percent = ((second_avg - first_avg) / first_avg) * 100 if first_avg else 0

        if abs(change_percent) < 5:
            trend = 'stable'
        elif change_percent > 0:
            trend = 'degrading'
        else:
            trend = 'improving'

        return {
            'trend': trend,
            'change_percent': change_percent,
            'first_half_avg_ms': first_avg,
            'second_half_avg_ms': second_avg,
            'sample_size': len(self.commands)
        }


# Global command history instance
command_history = CommandHistory()


def create_command(command_id: Optional[str] = None) -> TimedCommand:
    """
    Create a new timed command and add to history.

    Args:
        command_id: Optional command ID

    Returns:
        New TimedCommand instance
    """
    cmd = TimedCommand(command_id=command_id) if command_id else TimedCommand()
    command_history.add(cmd)
    return cmd


def get_command(command_id: str) -> Optional[TimedCommand]:
    """
    Retrieve a command from history by ID.

    Args:
        command_id: Command ID to find

    Returns:
        TimedCommand or None
    """
    for cmd in command_history.commands:
        if cmd.command_id == command_id:
            return cmd
    return None