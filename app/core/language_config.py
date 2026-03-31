
from dataclasses import dataclass

@dataclass
class LanguageConfig:
    image: str
    source_filename: str | None
    compile_command: str | None
    run_command: str
    requires_compile: bool

LANGUAGE_CONFIGS: dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        image="python:3.11",
        source_filename=None,
        compile_command=None,
        run_command="python -c '{code}'",
        requires_compile=False,
    ),
    "java": LanguageConfig(
        image="eclipse-temurin:17",
        source_filename="Main.java",
        compile_command="javac Main.java",
        run_command="java Main",
        requires_compile=True,
    ),
    "cpp": LanguageConfig(
        image="gcc:13",
        source_filename="main.cpp",
        compile_command="g++ main.cpp -O2 -o main",
        run_command="./main",
        requires_compile=True,
    ),
}