## Copyright (C) 2019, TomTom (http://tomtom.com).
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

################################################################################ Helper includes ##
<%!
from asciidoxy.generator.templates.helpers import has_any, tc
from asciidoxy.generator.templates.objc.helpers import ObjcTemplateHelper
from html import escape
%>
<%
helper = ObjcTemplateHelper(api, element, insert_filter)
%>
[#${element.id},reftext='${element.name}']
${api.inserted(element)}
[source,objectivec,subs="-specialchars,macros+"]
----
${escape(helper.method_signature(element))};
----

${element.brief}

${element.description}

% if has_any(element.params, element.exceptions, element.sections) or element.returns:
[cols='h,5a']
|===
% for section_title, section_text in element.sections.items():
| ${section_title}
| ${section_text | tc}

% endfor
% if element.params:
| Parameters
|
% for param in element.params:
`(${helper.print_ref(param.type)})${param.name}`::
${param.description | tc}

% endfor
% endif
% if element.returns and element.returns.type.name != "void":
| Returns
|
`${helper.print_ref(element.returns.type)}`::
${element.returns.description | tc}

% endif
% if element.exceptions:
| Throws
|
% for exception in element.exceptions:
`${helper.print_ref(exception.type)}`::
${exception.description | tc}

% endfor
%endif
|===
% endif
