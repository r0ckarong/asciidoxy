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

<%!
from asciidoxy.generator.templates.helpers import h1, has, tc
from asciidoxy.generator.templates.cpp.helpers import CppTemplateHelper
from html import escape
%>
[#${element.id},reftext='${element.full_name}']
${h1(leveloffset, element.name)}
${api.inserted(element)}

[source,cpp,subs="-specialchars,macros+"]
----
using ${element.name} = ${escape(CppTemplateHelper(api).print_ref(element.returns.type))}
----
${element.brief}

${element.description}

%if has(element.sections):
[cols='h,5a']
|===
% for section_title, section_text in element.sections.items():
| ${section_title}
| ${section_text | tc}

% endfor
|===
% endif
