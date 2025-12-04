"""Archive interview sessions for learning feedback."""

import json
from pathlib import Path
from datetime import datetime


class TranscriptArchiver:
    """Archive practice interview sessions."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.archive_dir = base_path / "archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive_session(self, question: str, answer: str, sources: list, profile: str):
        """Archive a single interview session."""
        # Create profile-specific archive directory
        profile_dir = self.archive_dir / profile
        today = datetime.now()
        date_dir = profile_dir / str(today.year) / f"{today.month:02d}" / f"{today.day:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate session file
        session_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        session_file = date_dir / f"session_{session_id}.json"

        session_data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "profile": profile,
            "question": question,
            "answer": answer,
            "sources_used": sources
        }

        try:
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            return True, f"Session archived: {session_file.name}"
        except Exception as e:
            return False, f"Failed to archive: {str(e)}"

    def get_sessions(self, profile: str, limit: int = 10) -> list:
        """Get recent archived sessions for a profile."""
        profile_dir = self.archive_dir / profile
        if not profile_dir.exists():
            return []

        # Collect all session files
        sessions = []
        for session_file in sorted(profile_dir.glob("**/*.json"), reverse=True)[:limit]:
            try:
                with open(session_file, 'r') as f:
                    sessions.append(json.load(f))
            except Exception:
                pass

        return sessions
