# __main__.py
# command-line interface for building and inspecting jfs disk images.
# josiah bergen, april 2026

import os
import sys
from array import array

from tap import Positional, Tap

from .image import BLOCK_WORDS, Image, JfsError, blocks_for, words_from_bytes, words_to_bytes


class FileArgs(Tap):
    image: Positional[str]  # the disk image
    binary: list[str] = []  # binary files, such as assembled programs: two bytes per word, low byte first
    text: list[str] = []    # text files, stored one character per word


class InfoArgs(Tap):
    image: Positional[str]  # the disk image


class ReadArgs(Tap):
    image: Positional[str]  # the disk image
    name: Positional[str]   # the file to read
    text: bool = False      # the file is text: write one byte per word


def add_files(image: Image, args: FileArgs) -> None:
    for path in args.binary:
        data = read_host_file(path)
        if len(data) % 2:
            raise JfsError(f"{path}: not a whole number of words ({len(data)} bytes). use --text for text files")
        image.add(os.path.basename(path), words_from_bytes(data))

    for path in args.text:
        image.add(os.path.basename(path), array("H", list(read_host_file(path))))


def create(args: FileArgs) -> None:
    """write a new image holding the given files"""
    image = Image.create()
    add_files(image, args)
    image.save(args.image)


def add(args: FileArgs) -> None:
    """add files to an existing image"""
    image = Image.load(args.image)
    add_files(image, args)
    image.save(args.image)


def info(args: InfoArgs) -> None:
    """print the volume's geometry and its files"""
    image = Image.load(args.image)
    files = image.files()

    print(f"{args.image}: {image.blocks} blocks ({image.blocks * BLOCK_WORDS * 2 // 1024} KiB), {len(image.free_blocks())} free")
    print(f"table at block {image.table_start} ({image.table_blocks} blocks), root at block {image.root_start} ({image.root_blocks} blocks), data from block {image.data_start}")
    print(f"{len(files)} of {image.root_entries} files")

    if files:
        print(f"\n{'name':<13}  {'words':>5}  {'blocks':>6}  {'start':>5}")
    for file in files:
        image.chain(file)  # reports a corrupt chain
        start = file.start if file.size else "-"
        print(f"{file.name:<13}  {file.size:>5}  {blocks_for(file.size):>6}  {start:>5}")


def read(args: ReadArgs) -> None:
    """write a file's contents to stdout"""
    contents = Image.load(args.image).read(args.name)

    if not args.text:
        data = words_to_bytes(contents)
    elif max(contents, default=0) > 0xFF:
        raise JfsError(f"{args.name}: not text (it holds words above 0xFF)")
    else:
        data = bytes(contents.tolist())

    sys.stdout.buffer.write(data)


COMMANDS = {
    "create": (create, FileArgs),
    "add": (add, FileArgs),
    "info": (info, InfoArgs),
    "read": (read, ReadArgs),
}


class Args(Tap):
    """build and inspect jfs disk images"""

    def configure(self) -> None:
        self.add_subparsers(dest="command", required=True)
        for name, (function, arguments) in COMMANDS.items():
            self.add_subparser(name, arguments, help=function.__doc__, description=function.__doc__)


def read_host_file(path: str) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        raise JfsError(f"cannot read {path}: {e.strerror}") from e


def main() -> None:
    try:
        args = Args().parse_args()
        COMMANDS[args.command][0](args)
    except JfsError as e:
        sys.exit(f"jfs: {e}")


if __name__ == "__main__":
    main()
