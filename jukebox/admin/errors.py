class MissingOptionalDependencyError(Exception):
    def __init__(self, subject: str, extra_name: str, run_command: str):
        super().__init__(subject)
        self.extra_name = extra_name
        self.run_command = run_command

    @property
    def install_hint(self) -> str:
        return (
            f"Optional `{self.extra_name}` dependencies are not installed. "
            f"Run `uv sync --extra {self.extra_name}` to install them. "
            f"Or run `uv run --extra {self.extra_name} {self.run_command}`."
        )
