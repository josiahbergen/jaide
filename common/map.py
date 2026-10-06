
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from jasm.language.ir.base import AlignDirectiveNode, DataDirectiveNode, InstructionNode, TimesDirectiveNode

type DirectiveNode = DataDirectiveNode | TimesDirectiveNode | AlignDirectiveNode

class SourceMapException(Exception):
    pass

@dataclass
class SourceWord:
    instruction: str
    index: int
    source: str
    breakpoint: bool = False


class SourceMap:
    def __init__(self):
        self.words: list[SourceWord] = []

    def reset(self) -> None:
        self.words.clear()

    def from_json(self, raw: bytes) -> None:
        self.words = [SourceWord(**word) for word in json.loads(raw)]

    def add_node(self, node: DirectiveNode | InstructionNode, bytes: bytearray, breakpoint: bool = False) -> None:
        for i in range(0, len(bytes), 2):
            # some instructions are more than one word, so we just need to add multiple entries
            # of the source node for every word that the instruction takes up in memory
            self.words.append(
                SourceWord(
                    instruction=str(node),
                    index=i // 2,
                    source=f"{Path(node.filename).name}:{node.line}",
                    breakpoint=breakpoint
                )
            )
            breakpoint = False  # only the first word of any instruction gets a breakpoint indicator

    def write(self, binary_path: str | Path) -> None:
        # write a source map file to the same directory as a binary,
        # keeping the same filename but with a .map.json extension: /bin/kernel.bin -> /bin/kernel.map.json

        map = Path(binary_path).with_suffix(".map.json")
        map.write_text(json.dumps([asdict(word) for word in self.words], indent=2) + "\n")


    def get_source(self, addr: int) -> str:
        if addr < 0 or addr >= len(self.words):
            return "unknown"
        source = self.words[addr]
        return f"{source.instruction}, word {source.index} (from {source.source})"