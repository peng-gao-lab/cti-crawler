from pathlib import Path


def source_directory(source: str, source_family: str | None) -> Path:
    if source_family == "activity_reports":
        return Path("activity_reports") / source
    return Path(source)


def source_storage(output_root: Path, source: str, source_family: str | None):
    directory = output_root / source_directory(source, source_family)
    legacy = output_root / source
    if directory != legacy and legacy.exists():
        if directory.exists():
            raise FileExistsError(f"Both old and new source directories exist: {legacy}, {directory}")
        directory.parent.mkdir(parents=True, exist_ok=True)
        legacy.rename(directory)
    return FileStorage(directory)


class FileStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, filename: str) -> Path:
        return self.root / filename

    def exists(self, filename: str) -> bool:
        return self.path(filename).is_file()

    def write(self, filename: str, content: bytes) -> Path:
        destination = self.path(filename)
        temporary = destination.with_name(f"{destination.name}.part")
        temporary.write_bytes(content)
        temporary.replace(destination)
        return destination
