# Copyright (C) 2019-2021, TomTom (http://tomtom.com).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Command line interface."""

import argparse
import json
import logging
import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from mako.exceptions import RichTraceback
from tqdm import tqdm

from ._version import __version__
from .api_reference import ApiReference
from .generator import process_adoc
from .model import json_repr
from .packaging import CollectError, PackageManager, SpecificationError
from .parser.doxygen import Driver as DoxygenDriver
from .path_utils import relative_path


def error(*args, **kwargs) -> None:
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


def asciidoctor(destination_dir: Path, out_file: Path, processed_file: Path, multipage: bool,
                backend: str, extra_args: Sequence[str], image_dir: Path) -> None:
    args = [
        "asciidoctor",
        "-D",
        str(destination_dir),
        "-o",
        str(out_file),
        "-b",
        backend,
        "-a",
        f"imagesdir@={image_dir}",
        str(processed_file),
    ]
    if multipage:
        args += ["-a", "multipage"]
    if extra_args:
        args += extra_args

    if platform.system() == "Windows":
        subprocess.run(args, shell=True, check=True)
    else:
        subprocess.run(" ".join(args), shell=True, check=True)


def output_extension(backend: str) -> Optional[str]:
    return {"html5": ".html", "pdf": ".pdf", "adoc": ".adoc"}.get(backend)


class PathArgument:
    _existing_dir: bool
    _existing_file: bool
    _new_dir: bool

    def __init__(self,
                 existing_dir: bool = False,
                 existing_file: bool = False,
                 new_dir: bool = False):
        self._existing_dir = existing_dir
        self._existing_file = existing_file
        self._new_dir = new_dir

    def __call__(self, value: str) -> Optional[Path]:
        if value is None:
            return None

        path = Path(value).resolve()

        if self._existing_dir and not path.is_dir():
            raise argparse.ArgumentTypeError(
                "{} does not point to an existing directory.".format(value))
        if self._existing_file and not path.is_file():
            raise argparse.ArgumentTypeError("{} does not point to an existing file.".format(value))
        if self._new_dir and path.is_file():
            raise argparse.ArgumentTypeError("{} points to an existing file.".format(value))
        if not self._new_dir and not path.parent.exists():
            raise argparse.ArgumentTypeError(
                "Directory to store {} in does not exist.".format(value))

        return path


def main(argv: Optional[Sequence[str]] = None) -> None:
    print(rf"""
    ___              _ _ ____  {__version__:>16}
   /   |  __________(_|_) __ \____  _  ____  __
  / /| | / ___/ ___/ / / / / / __ \| |/_/ / / /
 / ___ |(__  ) /__/ / / /_/ / /_/ />  </ /_/ /
/_/  |_/____/\___/_/_/_____/\____/_/|_|\__, /
                                      /____/
""")

    parser = argparse.ArgumentParser(description="Generate API documentation using AsciiDoctor",
                                     allow_abbrev=False)
    parser.add_argument("input_file",
                        metavar="INPUT_FILE",
                        type=PathArgument(existing_file=True),
                        help="Input AsciiDoc file.")
    parser.add_argument("-B",
                        "--base-dir",
                        metavar="BASE_DIR",
                        default=None,
                        type=PathArgument(existing_dir=True),
                        help="Base directory containing the document and resources. If no base"
                        " directory is specified, local include files cannot be found.")
    parser.add_argument("--image-dir",
                        metavar="IMAGE_DIR",
                        default=None,
                        type=PathArgument(existing_dir=True),
                        help="Directory containing images to include. If no image directory is"
                        " specified, only images in the `images` directory next to the input file"
                        " can be included.")
    parser.add_argument("-b",
                        "--backend",
                        metavar="BACKEND",
                        default="html5",
                        help="Set output backend format used by AsciiDoctor. Use special backend"
                        " `adoc` to produce AsciiDoc files only and not run AsciiDoctor on it.")
    parser.add_argument("--build-dir",
                        metavar="BUILD_DIR",
                        default="build",
                        type=PathArgument(new_dir=True),
                        help="Build directory.")
    parser.add_argument("-D",
                        "--destination-dir",
                        metavar="DESTINATION_DIR",
                        default=None,
                        type=PathArgument(new_dir=True),
                        help="Destination for generate documentation.")
    parser.add_argument("-s",
                        "--spec-file",
                        metavar="SPEC_FILE",
                        default=None,
                        type=PathArgument(existing_file=True),
                        help="Package specification file.")
    parser.add_argument("-v",
                        "--version-file",
                        metavar="VERSION_FILE",
                        default=None,
                        type=PathArgument(existing_file=True),
                        help="Version specification file.")
    parser.add_argument("-W",
                        "--warnings-are-errors",
                        action="store_true",
                        help="Stop processing input files when a warning is encountered.")
    parser.add_argument("--debug", action="store_true", help="Store debug information.")
    parser.add_argument("--log",
                        metavar="LOG_LEVEL",
                        default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the log level.")
    parser.add_argument("--force-language",
                        metavar="LANGUAGE",
                        help="Force language used when parsing doxygen XML files. Ignores the"
                        " language specified in the XML files.")
    parser.add_argument("--multipage", action="store_true", help="Generate multi-page document.")
    parser.add_argument("--template-dir",
                        metavar="TEMPLATE_DIR",
                        default=None,
                        type=PathArgument(existing_dir=True),
                        help="*Experimental* Directory containing custom templates to use instead"
                        " of the default templates shipped with AsciiDoxy. Templates found in this"
                        " directory will be used in favor of the default templates. Only when a"
                        " template is not found here, the default templates are used.")
    parser.add_argument("--cache-dir",
                        metavar="CACHE_DIR",
                        default=None,
                        type=PathArgument(new_dir=True),
                        help="Directory for caching generated python code for templates and input"
                        " documents. Reduces runtime for consecutive runs by skipping code"
                        "generation for unchanged files.")
    if argv is None:
        argv = sys.argv[1:]
    args, extra_args = parser.parse_known_args(argv)

    log_level = getattr(logging, args.log)
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    logger = logging.getLogger(__name__)

    if args.destination_dir is not None:
        destination_dir = args.destination_dir
    else:
        destination_dir = args.build_dir / "output"
    if args.cache_dir is not None:
        cache_dir = args.cache_dir
    else:
        cache_dir = args.build_dir / "cache"
    extension = output_extension(args.backend)
    if extension is None:
        logger.error(f"Backend {args.backend} is not supported.")
        sys.exit(1)

    pkg_mgr = PackageManager(args.build_dir, args.warnings_are_errors)
    if args.spec_file is not None:
        try:
            with tqdm(desc="Collecting packages     ", unit="pkg") as progress:
                pkg_mgr.collect(args.spec_file, args.version_file, progress)
        except SpecificationError:
            logger.exception("Failed to load package specifications.")
            sys.exit(1)
        except CollectError:
            logger.exception("Failed to collect packages.")
            sys.exit(1)

        xml_parser = DoxygenDriver(force_language=args.force_language)
        with tqdm(desc="Loading API reference   ", unit="pkg") as progress:
            pkg_mgr.load_reference(xml_parser, progress)

        with tqdm(desc="Resolving references    ", unit="ref") as progress:
            xml_parser.resolve_references(progress)

        if args.debug:
            logger.info("Writing debug data, sorry for the delay!")
            with (args.build_dir / "debug.json").open("w", encoding="utf-8") as f:
                json.dump(xml_parser.api_reference.elements, f, default=json_repr, indent=2)

        api_reference = xml_parser.api_reference
    else:
        api_reference = ApiReference()

    if args.backend == "adoc":
        pkg_mgr.work_dir = destination_dir
        clear_work_dir = False
    else:
        clear_work_dir = True
    pkg_mgr.set_input_files(args.input_file, args.base_dir, args.image_dir)
    with tqdm(desc="Preparing work directory", unit="pkg") as progress:
        in_doc = pkg_mgr.prepare_work_directory(args.input_file, clear_work_dir, progress)

    try:
        with tqdm(desc="Processing asciidoc     ", total=1, unit="file") as progress:
            documents = process_adoc(in_doc,
                                     api_reference,
                                     pkg_mgr,
                                     warnings_are_errors=args.warnings_are_errors,
                                     multipage=args.multipage,
                                     custom_template_dir=args.template_dir,
                                     cache_dir=cache_dir,
                                     progress=progress)

    except:  # noqa: E722
        logger.error(human_traceback(pkg_mgr))
        sys.exit(1)

    if args.backend != "adoc":
        for doc in tqdm(documents, desc="Running asciidoctor     ", unit="doc"):
            if args.multipage and doc.is_embedded:
                continue
            if not args.multipage and not doc.is_root:
                continue

            out_file = destination_dir / doc.relative_path.with_suffix(extension)
            rel_image_dir = relative_path(doc.work_file, pkg_mgr.image_work_dir)
            asciidoctor(destination_dir, out_file, doc.work_file, args.multipage, args.backend,
                        extra_args, rel_image_dir)
            logger.info(f"Generated: {out_file}")

    if args.backend != "pdf":
        with tqdm(desc="Copying images          ", unit="pkg") as progress:
            pkg_mgr.make_image_directory(destination_dir, progress)


def human_traceback(pkg_mgr: PackageManager) -> str:
    """Generate a human readable traceback the current exception. To be used inside an except
    clause.

    Exceptions triggered inside AsciiDoc are handled specially:
     - Lines inside AsciiDoc files are resolved to the original AsciiDoc lines.
     - AsciiDoxy code loading the AsciiDoc files is skipped.
     - Additional Mako loading due to includes is skipped.
    """
    traceback = RichTraceback()

    message = [""]
    has_adoc = False
    pending_traceback: List[str] = []
    for filename, lineno, function, line in traceback.traceback:
        if filename.endswith(".adoc"):
            pending_traceback.clear()

            package_name, original_file = pkg_mgr.find_original_file(Path(filename))
            if package_name and package_name != "INPUT":
                filename = f"{package_name}:/{original_file}"
            elif original_file is not None:
                filename = str(original_file)
            message.append(f"  File {filename}, line {lineno}, in AsciiDoc\n    {line}")
            has_adoc = True
        elif "/mako/" in filename:
            continue
        else:
            pending_traceback.append(f"  File {filename}, line {lineno}, in "
                                     f"{function}\n    {line}")
    if pending_traceback:
        message.extend(pending_traceback)

    if has_adoc:
        message[0] = f"Error while processing AsciiDoc files:\n{traceback.error}\nTraceback:"
    else:
        message[0] = f"Internal error:\n{traceback.error}\nTraceback:"

    return "\n".join(message)


if __name__ == "__main__":
    main()
