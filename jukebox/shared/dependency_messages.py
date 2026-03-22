def optional_extra_dependency_message(subject: str, extra_name: str, source_command: str) -> str:
    return (
        f"{subject} requires the optional `{extra_name}` dependencies.\n\n"
        "If you installed the package, reinstall it with extras enabled using your package manager:\n"
        f"  pip install 'gukebox[{extra_name}]'\n\n"
        "If you're running from a source checkout:\n"
        f"  uv sync --extra {extra_name}\n"
        f"or \n"
        f"  uv run --extra {extra_name} {source_command}"
    )
