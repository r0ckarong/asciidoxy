# Copyright (C) 2019, TomTom (http://tomtom.com).
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
"""Context of the document being generated."""

import copy
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, MutableMapping, NamedTuple, Optional, Tuple

from tqdm import tqdm

from ..api_reference import ApiReference
from ..config import Configuration
from ..document import Document, Package
from ..model import ReferableElement
from ..packaging import PackageManager, UnknownFileError
from .cache import DocumentCache, TemplateCache
from .errors import ConsistencyError, DuplicateAnchorError, UnknownAnchorError
from .filters import InsertionFilter

logger = logging.getLogger(__name__)


class Environment(object):
    """Namespace for holding environment variables to be shared between different AsciiDoc files.

    AsciiDoc files can assign variables in the environment namespace to be reused in other AsciiDoc
    files that are included from it. Like other concepts in AsciiDoxy, the changes should only
    apply to the current file, and any include from the current file. The parent namespace should
    remain unchanged.

    This class is intentionaly simple. New variables can be added to an instance by simply
    assigining them:

      env = Environment()
      env.new_var = "value"

    To copy the environment to subcontexts use copy.copy(). This prevents changing the variables
    in the parent scopes.
    """


class StackFrame(NamedTuple):
    """Frame on the stack of AsciiDoxy commands being executed.

    The sequence of stack frames can be used to provide detailed feedback on how a certain action
    has been called. This is especially useful for a chain of actions generated by AsciiDoxy
    itself.

    Attributes:
        command:  Description of the command being executed.
        file:     If applicable, the file from which the command originated. Empty for commands
                      originating from other AsciiDoxy commands.
        package:  If applicable, the package containing the file.
        internal: True if the stack frame is for an internal method call.
    """
    command: str
    file: Optional[Path]
    package: Optional[str]
    internal: bool


def stacktrace(trace: List[StackFrame], prefix: str = "") -> str:
    """Generate a string representation of a sequence of stack frames.

    Args:
        trace:  Sequence of stack frames.
        prefix: Optional prefix for each line. E.g. to add indentation.

    Returns:
        String representation of the stack trace.
    """
    if not trace:
        return ""

    trace = trace[:]
    lines = []

    if not trace[0].internal:
        lines.append(f"{prefix}Commands in input files:")
    while trace and not trace[0].internal:
        if trace[0].package and trace[0].package != Package.INPUT_PACKAGE_NAME:
            pkg = f"{trace[0].package}:/"
        else:
            pkg = ""
        lines.append(f"{prefix}  {pkg}{trace[0].file}:\n{prefix}    {trace[0].command}")
        trace.pop(0)

    if trace and trace[0].internal:
        lines.append(f"{prefix}Internal AsciiDoxy commands:")
    while trace:
        lines.append(f"{prefix}    {trace[0].command}")
        trace.pop(0)

    return "\n".join(lines)


class AnchorData(NamedTuple):
    """Data for inserted anchors."""
    document: Document
    link_text: Optional[str]


class InsertData(NamedTuple):
    """Data for tracking inserted elements."""
    document: Document
    stacktrace: List[StackFrame]


class Context(object):
    """Contextual information about the document being generated.

    This information is meant to be shared with all included documents as well.

    Attributes:
        namespace:             Current namespace to use when looking up references.
        language:              Default language to use when looking up references.
        insert_filter:         Filter used to select members of elements to insert.
        env:                   Environment variables to share with subdocuments.
        reference:             API reference information.
        linked:                All elements to which links are inserted in the documentation.
        inserted:              All elements that have been inserted in the documentation.
        anchors:               Mapping from flexible anchors to the containing files.
        call_stack:            Stack of actions resulting in the current action.
        document:              Current document being processed.
        documents:             All known documents.
        document_stack:        Stack of documents containing/including the current document.
        config:                The configuration deduced from the command line arguments.
    """
    namespace: Optional[str] = None
    language: Optional[str] = None
    source_language: Optional[str] = None
    insert_filter: InsertionFilter
    env: Environment

    reference: ApiReference
    package_manager: PackageManager
    progress: Optional[tqdm] = None

    linked: Dict[str, List[List[StackFrame]]]
    inserted: MutableMapping[str, InsertData]
    anchors: Dict[str, AnchorData]
    call_stack: List[StackFrame]

    document: Document
    documents: Dict[Path, Document]
    document_stack: List[Document]

    templates: TemplateCache
    document_cache: DocumentCache

    config: Configuration

    def __init__(self, reference: ApiReference, package_manager: PackageManager, document: Document,
                 config: Configuration):
        self.insert_filter = InsertionFilter(members={"prot": ["+public", "+protected"]})
        self.env = Environment()

        self.reference = reference
        self.package_manager = package_manager

        self.linked = defaultdict(list)
        self.inserted = {}
        self.anchors = {}
        self.document = document
        self.call_stack = []

        self.documents = {document.relative_path: document}
        self.document_stack = [document]

        self.templates = TemplateCache(config.template_dir, config.cache_dir)
        self.document_cache = DocumentCache(config.cache_dir)

        self.config = config

    def insert(self, element: ReferableElement) -> None:
        """Register insertion of an element."""
        assert element.id
        if element.id in self.inserted:
            trace = self.inserted[element.id].stacktrace
            msg = (f"Duplicate insertion of {element.name}.\nTrying to insert at:\n"
                   f"{stacktrace(self.call_stack, prefix='  ')}\nPreviously inserted at:\n"
                   f"{stacktrace(trace, prefix='  ')}")
            if self.config.warnings_are_errors:
                raise ConsistencyError(msg)
            else:
                logger.warning(msg)
        self.inserted[element.id] = InsertData(self.document, self.call_stack[:])

    def sub_context(self, document: Document) -> "Context":
        """Create a new sub context to process `document`."""
        sub = Context(reference=self.reference,
                      package_manager=self.package_manager,
                      document=document,
                      config=self.config)

        # Copies
        sub.namespace = self.namespace
        sub.language = self.language
        sub.source_language = self.source_language
        sub.env = copy.copy(self.env)
        sub.insert_filter = copy.deepcopy(self.insert_filter)
        sub.document_stack = self.document_stack[:]
        sub.document_stack.append(document)

        # References
        sub.linked = self.linked
        sub.inserted = self.inserted
        sub.anchors = self.anchors
        sub.progress = self.progress
        sub.call_stack = self.call_stack
        sub.documents = self.documents
        sub.templates = self.templates
        sub.document_cache = self.document_cache

        return sub

    def file_with_element(self, element_id: str) -> Optional[Document]:
        """Find the file containing given element.

        Returns:
            The document containing the element or None if the element is not inserted anywhere.
        """
        if not self.config.multipage or element_id not in self.inserted:
            return None

        containing_doc = self.inserted[element_id].document
        assert containing_doc is not None
        if self.document is not containing_doc:
            return containing_doc
        else:
            return None

    def link_to_element(self, element_id: str) -> None:
        """Register a link to an element."""
        self.linked[element_id].append(self.call_stack[:])

    def find_document(self, package_name: Optional[str], rel_path: Optional[Path]) -> Document:
        """Find a document if it exists.

        Args:
            package_name: Name of the package containing the file. Empty to look in the input files.
            rel_path:     Relative path to the file. Empty to take the default file, if present.

        Raises:
            UnknownPackageError: There is no package with name `package_name`.
            UnknownFileError:    The file does not exist, or the package does not have a default
                                     file.
        """
        assert package_name or rel_path

        if rel_path is None:
            default_doc = self.package_manager.make_document(package_name)
            known_doc = self.documents.get(default_doc.relative_path)
            if known_doc is None:
                self.documents[default_doc.relative_path] = default_doc
                return default_doc
            return known_doc

        else:

            known_doc = self.documents.get(rel_path)
            if known_doc is None:
                doc = self.package_manager.make_document(package_name, rel_path)
                self.documents[doc.relative_path] = doc
                return doc
            elif package_name and known_doc.package.name != package_name:
                raise UnknownFileError(package_name, str(rel_path))
            return known_doc

    def link_to_document(self, document: Document) -> Path:
        """Determine the correct path to link to a document.

        The exact path differs for single and multipage mode and whether a file is embedded or not.
        AsciiDoctor processes links in included files as if they are originating from the top level
        file.
        """
        if not document.is_embedded:
            # File is not embedded, link to original file name
            return self.output_document.relative_path_to(document)

        elif len(document.embedded_in) == 1:
            # File is only embedded in one file, link to that file
            return self.output_document.relative_path_to(document.find_embedder())

        elif document.is_embedded_in(self.document):
            # File is embedded multiple time, can only link if it is embedded in the
            # current document
            return Path(self.document.relative_path.name)

        else:
            raise ConsistencyError(f"Cannot resolve link to embedded file {document}: The same file"
                                   " is embedded multiple times. Either embed the file"
                                   " in only one file, or only link to it from the"
                                   " files it is embedded in.")

    def docinfo_footer_file(self) -> Path:
        """Path to the optional file containing a docinfo footer."""
        return self.output_document.docinfo_footer_file

    def register_anchor(self, name: str, link_text: Optional[str]) -> None:
        """Register insertion of a flexible, global anchor.

        Raises:
            DuplicateAnchorError: There is already an anchor with the same name.
        """
        if name in self.anchors:
            raise DuplicateAnchorError(name)
        self.anchors[name] = AnchorData(self.document, link_text)

    def link_to_anchor(self, name: str) -> Tuple[Path, Optional[str]]:
        """Get the path and optionally the link text for a flexible, global anchor.

        Raises:
            UnknownAnchorError: There is no anchor with given name.
        """
        anchor = self.anchors.get(name)
        if anchor is None:
            raise UnknownAnchorError(name)
        return self.link_to_document(anchor.document), anchor.link_text

    def push_stack(self,
                   command: str,
                   document: Optional[Document] = None,
                   package: Optional[str] = None,
                   internal: bool = False) -> None:
        """Push a command to the stack for error reporting."""
        self.call_stack.append(
            StackFrame(command, document.relative_path if document else None, package, internal))

    def pop_stack(self) -> None:
        """Pop a command from the stack for error reporting."""
        self.call_stack.pop(-1)

    @property
    def output_document(self):
        """Generated output document that should be used as a base for resolving relative paths."""
        if self.config.multipage:
            # In multipage mode all links are relative to the generated page
            if self.document.is_embedded:
                for doc in reversed(self.document_stack):
                    if not doc.is_embedded:
                        return doc
                else:
                    return self.document_stack[0]
            else:
                return self.document
        else:
            # In singlepage mode all links need to be relative to the root file
            return self.document.root()
