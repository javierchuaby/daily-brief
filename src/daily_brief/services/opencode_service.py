"""OpenCode AI service implementation."""

import subprocess

from daily_brief.interfaces import AIService


class OpenCodeAIService(AIService):
    """AI service using OpenCode CLI."""

    def synthesize(self, data: dict, prompt: str) -> str:
        """Synthesize content using OpenCode AI.

        Args:
            data: Raw data to be used as context
            prompt: Instruction prompt for the AI

        Returns:
            Generated content as a string

        Raises:
            RuntimeError: If OpenCode CLI fails
            FileNotFoundError: If OpenCode CLI not available
        """
        # Construct prompt with data reference
        # The data will be passed via a temporary file
        data_file = "/tmp/fine_grained_data.json"
        with open(data_file, "w") as f:
            import json

            json.dump(data, f, indent=2, default=str)

        full_prompt = f"Read data from {data_file}. {prompt}"

        try:
            result = subprocess.run(
                ["opencode", "run", "-m", "soclaas/qwen3.8:27b", full_prompt],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                raise RuntimeError(f"OpenCode AI synthesis failed: {result.stderr}")
        except FileNotFoundError:
            raise FileNotFoundError("OpenCode CLI not found. Please install opencode.")
