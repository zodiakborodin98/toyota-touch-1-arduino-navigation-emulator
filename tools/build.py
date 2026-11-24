#!/usr/bin/env python3
"""Build the Nano firmware using the Arduino AVR Boards 1.8.8 package."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SKETCH = ROOT / "firmware" / "Tirta_NAVI_178"
REFERENCE = ROOT / "release" / "toyota-touch-nano.hex"
SKETCH_SOURCES = ["Tirta_NAVI_178.ino", "AVCLanDrv.cpp", "AVCLanNavi.cpp", "BuffSerial.cpp"]


def build(package, work):
    platform = package / "hardware" / "avr" / "1.8.8"
    core = platform / "cores" / "arduino"
    variant = platform / "variants" / "eightanaloginputs"
    tools = package / "tools" / "avr-gcc" / "7.3.0-atmel3.6.1-arduino7" / "bin"
    if not (core / "Arduino.h").is_file() or not tools.is_dir():
        raise SystemExit("Expected Arduino AVR Boards 1.8.8 and its AVR GCC under --arduino-package.")

    def run(tool, *args):
        subprocess.run([str(tools / tool), *map(str, args)], cwd=work, check=True)

    board = ["-mmcu=atmega328p", "-DF_CPU=16000000UL", "-DARDUINO=10819",
             "-DARDUINO_AVR_NANO", "-DARDUINO_ARCH_AVR", "-I" + str(core), "-I" + str(variant)]
    sections = ["-ffunction-sections", "-fdata-sections"]
    core_objects = []
    for src in sorted(core.iterdir(), key=lambda path: path.name):
        if src.suffix not in {".c", ".cpp", ".S"}:
            continue
        obj = work / (src.name + ".o")
        if src.suffix == ".cpp":
            run("avr-g++", "-c", "-Os", "-std=gnu++11", "-fpermissive", "-fno-exceptions",
                "-fno-threadsafe-statics", "-Wno-error=narrowing", *sections, "-flto",
                *board, src, "-o", obj)
        elif src.suffix == ".c":
            run("avr-gcc", "-c", "-Os", "-std=gnu11", *sections, "-flto",
                "-fno-fat-lto-objects", *board, src, "-o", obj)
        else:
            run("avr-gcc", "-c", "-x", "assembler-with-cpp", "-flto", *board, src, "-o", obj)
        core_objects.append(obj)
    run("avr-gcc-ar", "rcs", "core.a", *core_objects)

    # The hardware-tested build compiled only the Arduino core with LTO.
    objects = []
    for name in SKETCH_SOURCES:
        obj = work / (name + ".o")
        run("avr-g++", "-c", "-x", "c++", "-Os", "-std=gnu++11", "-fno-exceptions",
            *sections, *board, "-I" + str(SKETCH), "-include", core / "Arduino.h",
            SKETCH / name, "-o", obj)
        objects.append(obj)

    run("avr-gcc", "-Os", "-Wl,--gc-sections", "-mmcu=atmega328p", "-o", "nano.elf",
        *objects, "core.a", "-lm")
    run("avr-objcopy", "-O", "ihex", "-R", ".eeprom", "nano.elf", "nano.hex")
    run("avr-size", "-C", "--mcu=atmega328p", "nano.elf")
    # Match the released Intel HEX text on every host, including its line endings.
    return b"\r\n".join((work / "nano.hex").read_bytes().splitlines()) + b"\r\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arduino-package", required=True, type=Path,
                        help="Arduino data directory's packages/arduino folder")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "toyota-touch-nano.hex")
    parser.add_argument("--verify", action="store_true",
                        help="also require identical Intel HEX records to the hardware-tested release")
    args = parser.parse_args()
    if args.output.resolve() == REFERENCE.resolve():
        parser.error("Use a build output path separate from the reference release.")
    with tempfile.TemporaryDirectory(prefix="toyota-nano-") as directory:
        firmware = build(args.arduino_package.resolve(), Path(directory))
    if args.verify and firmware.splitlines() != REFERENCE.read_bytes().splitlines():
        raise SystemExit("Rebuilt Intel HEX differs from the reference release.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(firmware)
    print(f"{hashlib.sha256(firmware).hexdigest()}  {args.output}")
    if args.verify:
        print("All Intel HEX records match the hardware-tested release.")


if __name__ == "__main__":
    main()
