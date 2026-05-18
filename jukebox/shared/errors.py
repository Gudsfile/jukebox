class MissingOptionalDependencyError(Exception):
    def __init__(self, subject: str, extra_name: str, run_command: str):
        self.subject = subject
        self.extra_name = extra_name
        self.run_command = run_command
        super().__init__(self.install_hint)

    @property
    def concise_hint(self) -> str:
        return (
            f"Optional `{self.extra_name}` dependencies are not installed. "
            f"Install them with: pip install 'gukebox[{self.extra_name}]'"
        )

    @property
    def install_hint(self) -> str:
        return (
            f"{self.subject} requires the optional `{self.extra_name}` dependencies.\n\n"
            "If you installed the package, reinstall it with extras enabled using your package manager:\n"
            f"  pip install 'gukebox[{self.extra_name}]'\n\n"
            "If you're running from a source checkout:\n"
            f"  uv sync --extra {self.extra_name}\n"
            f"or\n"
            f"  uv run --extra {self.extra_name} {self.run_command}"
        )
