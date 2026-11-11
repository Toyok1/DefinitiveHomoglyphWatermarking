import argparse
import json
import re
import urllib.request
from pathlib import Path


VERSION = "18.0.0"
SOURCE_URL = "https://www.unicode.org/Public/security/latest/confusables.txt"
CODE_POINT_PATTERN = re.compile(r"^[0-9A-F]{4,6}$")


def parse_code_points(value: str) -> list[int]:
    code_points = [int(item, 16) for item in value.split()]
    if not code_points:
        raise ValueError("A mapping has an empty code-point sequence")
    if any(point > 0x10FFFF or 0xD800 <= point <= 0xDFFF for point in code_points):
        raise ValueError(f"Invalid Unicode scalar value in sequence: {value}")
    if any(not CODE_POINT_PATTERN.fullmatch(item) for item in value.split()):
        raise ValueError(f"Invalid code-point notation: {value}")
    return code_points


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a JSON export of Unicode UTS #39 confusable mappings."
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("confusables.json"),
        help="Output JSON path (default: confusables.json beside this script)",
    )
    args = parser.parse_args()

    request = urllib.request.Request(
        SOURCE_URL, headers={"User-Agent": "UnicodeConfusablesJsonGenerator/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read().decode("utf-8")

    source_date = None
    version = None
    copyright_notice = None
    mappings = []
    for line in content.splitlines():
        if line.startswith("# Date:"):
            source_date = line.partition(":")[2].strip().split(",", 1)[0]
            continue
        if line.startswith("# Version:"):
            version = line.partition(":")[2].strip()
            continue
        if line.startswith("# ©"):
            copyright_notice = line[2:].strip()
            continue

        record = line.partition("#")[0].strip()
        if not record:
            continue
        fields = [field.strip() for field in record.split(";")]
        if len(fields) != 3:
            raise ValueError(f"Unexpected confusables record: {line}")

        source, target, mapping_type = fields
        source_points = parse_code_points(source)
        target_points = parse_code_points(target)
        mappings.append(
            {
                "source": {
                    "codePoints": [f"{point:04X}" for point in source_points],
                    "text": "".join(map(chr, source_points)),
                },
                "target": {
                    "codePoints": [f"{point:04X}" for point in target_points],
                    "text": "".join(map(chr, target_points)),
                },
                "type": mapping_type,
            }
        )

    if version != VERSION or not source_date or not copyright_notice or not mappings:
        raise ValueError(
            f"Unexpected source metadata or empty data: version={version!r}, "
            f"date={source_date!r}, copyright={copyright_notice!r}, "
            f"mappings={len(mappings)}"
        )

    result = {
        "metadata": {
            "standard": "Unicode Technical Standard #39",
            "unicodeVersion": version,
            "sourceDate": source_date,
            "source": SOURCE_URL,
            "copyright": copyright_notice,
            "license": "https://www.unicode.org/terms_of_use.html",
            "scope": (
                "Official UTS #39 confusable skeleton mappings across Unicode "
                "scripts. Mappings are directional and may contain sequences. "
                "Unicode does not classify these entries by language; this is "
                "not an exhaustive catalog of every context-dependent visual "
                "resemblance."
            ),
            "mappingCount": len(mappings),
        },
        "mappings": mappings,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(mappings)} mappings to {args.output}")


if __name__ == "__main__":
    main()
